import logging
import re
from datetime import timedelta
import unicodedata

from django.db import connection
from django.db.models import F
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from accounts.models import BreakdownClassificationJob, RDSCatalog
from accounts.breakdown_event_category import resolve_event_category


logger = logging.getLogger(__name__)
AUTO_CLASSIFICATION_THRESHOLD = 0.25
WORD_SIMILARITY_WEIGHT = 0.65
CHAR_SIMILARITY_WEIGHT = 0.35
MAX_JOB_ATTEMPTS = 3
PROCESSING_LEASE = timedelta(minutes=15)

ABBREVIATION_EXPANSIONS = {
    "fm": "external grid failure breakdown",
    "gf": "external grid fault",
    "gd": "external grid downtime",
    "gen": "generator",
    "brg": "bearing",
    "e/f": "earth fault",
    "ef": "earth fault",
    "ibs": "pitch system",
    "ips": "pitch system",
    "fdr": "feeder",
    "gbx": "gearbox",
    "wtg": "wind turbine",
    "eb": "external electricity board grid",
    "nde": "non drive end",
    "de": "drive end",
    "luber": "lubrication",
    "vcb": "circuit breaker switchgear",
    "rmu": "ring main unit switchgear",
    "hpu": "hydraulic power unit",
    "igbt": "insulated gate bipolar transistor",
    "slipring": "slip ring",
}

RULE_BASED_MATCHES = (
    (r"\b(external grid|grid outage|grid failure|grid fault|grid downtime|utility substation|load shedding|33kv line)\b", "MXA10"),
    (r"\b(generator|gen)\b.*\b(bearing|drive end|non drive end|de|nde)\b|\b(bearing|drive end|non drive end)\b.*\b(generator|gen)\b", "MDE20"),
    (r"\b(stator|winding|slip ring|carbon brush|phase sequence)\b", "MDE10"),
    (r"\b(generator cooling fan|cooling fan motor|generator heat exchanger)\b", "MDE30"),
    (r"\b(rotor blade|blade shell|blade bearing|blade inspection|rotor lock)\b", "MDA10"),
    (r"\bpitch bearing\b", "MDA10"),
    (r"\b(pitch motor|pitch drive|pitch battery|pitch converter|pitch system|feathering)\b", "MDA20"),
    (r"\b(yaw brake|yaw bearing|hydraulic yaw brake|yaw brake puck)\b", "MDY20"),
    (r"\b(yaw motor|yaw drive|yaw pinion|yaw counter)\b", "MDY10"),
    (r"\b(main shaft|main bearing|plummer block|pillow block)\b", "MDK10"),
    (r"\b(oil filter|lubrication pump|oil heat exchanger|gearbox oil|oil inlet temperature)\b", "MDK30"),
    (r"\b(gearbox|high speed shaft|planetary stage|mechanical brake|brake disk)\b", "MDK20"),
    (r"\bpitch\b", "MDA20"),
    (r"\b(power converter|converter igbt|igbt|inverter|dc link|thyristor)\b", "MSA10"),
    (r"\b(internal feeder|protection relay|circuit breaker|switchgear|vcb|rmu|earth fault relay|overcurrent relay)\b", "MSA20"),
    (r"\b(main transformer|nacelle transformer|busbar|buchholz)\b", "MSA30"),
    (r"\b(main plc|nacelle plc|tower plc|anemometer|wind vane|safety chain|safety loop|emergency button)\b", "MKC10"),
    (r"\b(hydraulic power unit|hydraulic motor|hydraulic pressure|hydraulic oil reservoir|accumulator|hpu)\b", "MHD10"),
    (r"\b(tower shell|nacelle frame|bedplate|foundation|anchor bolt)\b", "UMD10"),
)


def _catalog_text(entry):
    return " ".join(
        value.strip()
        for value in (
            entry.rds_code,
            getattr(entry, "system_code", ""),
            entry.system_name,
            getattr(entry, "subsystem_name", ""),
            entry.standard_component,
            entry.description or "",
            getattr(entry, "canonical_keywords", ""),
        )
        if value and value.strip()
    )


def _preprocess_text(value):
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    if not text or text in {"none", "nan", "null"}:
        return ""
    for abbreviation, expansion in ABBREVIATION_EXPANSIONS.items():
        text = re.sub(
            rf"(?<!\w){re.escape(abbreviation)}(?!\w)",
            f" {expansion} ",
            text,
        )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _entry_keyword_match_score(entry, text):
    keywords = getattr(entry, "canonical_keywords", "") or ""
    matched_token_counts = []
    for keyword in re.split(r"[,;\n|]+", keywords):
        normalized_keyword = _preprocess_text(keyword)
        if not normalized_keyword:
            continue
        if re.search(rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)", text):
            matched_token_counts.append(len(normalized_keyword.split()))
    if not matched_token_counts:
        return 0.0
    specificity = min(max(matched_token_counts), 5)
    return min(0.82, 0.67 + specificity * 0.03)


def build_catalog_matcher(catalog_entries):
    catalog_entries = list(
        catalog_entries if catalog_entries is not None else
        RDSCatalog.objects.filter(is_active=True)
    )
    if not catalog_entries:
        raise ValueError("The active RDS catalog is empty.")

    catalog_texts = [_preprocess_text(_catalog_text(entry)) for entry in catalog_entries]
    word_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        lowercase=True,
        sublinear_tf=True,
    )
    char_vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        lowercase=True,
        strip_accents="unicode",
        sublinear_tf=True,
    )
    word_catalog_matrix = word_vectorizer.fit_transform(catalog_texts)
    char_catalog_matrix = char_vectorizer.fit_transform(catalog_texts)
    catalog_by_code = {
        entry.rds_code.upper(): entry
        for entry in catalog_entries
    }

    def match(remark):
        text = _preprocess_text(remark)
        if not text:
            return catalog_entries[0], 0.0

        for pattern, rds_code in RULE_BASED_MATCHES:
            entry = catalog_by_code.get(rds_code)
            if entry is not None and re.search(pattern, text):
                return entry, 0.95

        word_scores = cosine_similarity(
            word_vectorizer.transform([text]),
            word_catalog_matrix,
        )[0]
        char_scores = cosine_similarity(
            char_vectorizer.transform([text]),
            char_catalog_matrix,
        )[0]
        combined_scores = (
            WORD_SIMILARITY_WEIGHT * word_scores
            + CHAR_SIMILARITY_WEIGHT * char_scores
        )
        for index, entry in enumerate(catalog_entries):
            combined_scores[index] = max(
                combined_scores[index],
                _entry_keyword_match_score(entry, text),
            )

        best_index = int(combined_scores.argmax())
        confidence = float(combined_scores[best_index])
        return catalog_entries[best_index], confidence

    return match


def classify_breakdown_remark(remark, catalog_entries=None):
    return build_catalog_matcher(catalog_entries)(remark)


def _validate_table_name(table_name):
    if not re.fullmatch(r"[a-zA-Z0-9_]+", table_name):
        raise ValueError("Invalid breakdown table name.")


def _claim_pending_jobs(batch_size):
    now = timezone.now()
    expired_before = now - PROCESSING_LEASE
    BreakdownClassificationJob.objects.filter(
        status=BreakdownClassificationJob.Status.PROCESSING,
        updated_at__lt=expired_before,
    ).update(
        status=BreakdownClassificationJob.Status.PENDING,
        updated_at=now,
    )

    candidates = list(
        BreakdownClassificationJob.objects.filter(
            status=BreakdownClassificationJob.Status.PENDING
        ).order_by("created_at", "id").values_list("id", flat=True)[:batch_size]
    )
    claimed_ids = []
    for job_id in candidates:
        claimed = BreakdownClassificationJob.objects.filter(
            id=job_id,
            status=BreakdownClassificationJob.Status.PENDING,
        ).update(
            status=BreakdownClassificationJob.Status.PROCESSING,
            attempts=F("attempts") + 1,
            updated_at=now,
        )
        if claimed:
            claimed_ids.append(job_id)
    return list(
        BreakdownClassificationJob.objects.filter(id__in=claimed_ids).order_by("id")
    )


def _classify_job(job, match_catalog):
    _validate_table_name(job.table_name)
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{job.table_name}`")
        columns = {row[0].lower() for row in cursor.fetchall()}
        required = {
            "id", "breakdown_remarks", "rds_code", "system_name",
            "standard_component", "classification_status",
            "classification_confidence", "classification_processed_at",
        }
        missing = required - columns
        if missing:
            raise ValueError(
                f"Breakdown table is missing classification columns: {', '.join(sorted(missing))}"
            )
        optional_fields = ("event_category", "duration_hrs")
        selected_fields = ["`breakdown_remarks`"]
        for field in optional_fields:
            selected_fields.append(
                f"`{field}`" if field in columns else f"NULL AS `{field}`"
            )
        cursor.execute(
            f"SELECT {', '.join(selected_fields)} "
            f"FROM `{job.table_name}` WHERE `id` = %s",
            [job.record_id],
        )
        record = cursor.fetchone()
        if record is None:
            return "record_missing"

        remark, event_category, duration_hrs = record

        entry, confidence = match_catalog(remark)
        processed_at = timezone.now()
        classification_status = (
            "CLASSIFIED"
            if confidence >= AUTO_CLASSIFICATION_THRESHOLD
            else "LOW_CONFIDENCE"
        )
        resolved_event_category = resolve_event_category(
            event_category,
            entry.rds_code,
            remark,
            duration_hrs,
        )
        assignments = [
            "`rds_code` = %s",
            "`system_name` = %s",
            "`standard_component` = %s",
            "`classification_status` = %s",
            "`classification_confidence` = %s",
            "`classification_processed_at` = %s",
        ]
        update_values = [
            entry.rds_code,
            entry.system_name,
            entry.standard_component,
            classification_status,
            confidence,
            processed_at,
        ]
        if "event_category" in columns:
            assignments.append("`event_category` = %s")
            update_values.append(resolved_event_category)
        update_values.append(job.record_id)
        cursor.execute(
            f"UPDATE `{job.table_name}` SET {', '.join(assignments)} "
            "WHERE `id` = %s",
            update_values,
        )
    return classification_status.lower()


def process_classification_batch(batch_size=100):
    jobs = _claim_pending_jobs(batch_size)
    if not jobs:
        return {"claimed": 0, "classified": 0, "low_confidence": 0, "failed": 0}

    catalog_entries = list(RDSCatalog.objects.filter(is_active=True).order_by("rds_code"))
    matcher_error = None
    try:
        match_catalog = build_catalog_matcher(catalog_entries) if jobs else None
    except Exception as error:
        match_catalog = None
        matcher_error = error
    counts = {"claimed": len(jobs), "classified": 0, "low_confidence": 0, "failed": 0}
    for job in jobs:
        try:
            if matcher_error:
                raise matcher_error
            result = _classify_job(job, match_catalog)
            job.status = BreakdownClassificationJob.Status.COMPLETED
            job.last_error = ""
            job.save(update_fields=["status", "last_error", "updated_at"])
            if result == "low_confidence":
                counts["low_confidence"] += 1
            elif result == "classified":
                counts["classified"] += 1
        except Exception as error:
            logger.exception(
                "Breakdown classification failed for %s record %s",
                job.table_name,
                job.record_id,
            )
            job.last_error = str(error)[:4000]
            job.status = (
                BreakdownClassificationJob.Status.FAILED
                if job.attempts >= MAX_JOB_ATTEMPTS
                else BreakdownClassificationJob.Status.PENDING
            )
            job.save(update_fields=["status", "last_error", "updated_at"])
            counts["failed"] += 1
    return counts
