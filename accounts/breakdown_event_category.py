import re


OEM_CATEGORY_SHORTHAND_MAP = {
    "S": "SCHEDULED",
    "SCH": "SCHEDULED",
    "PM": "SCHEDULED",
    "PREV": "SCHEDULED",
    "MAINT": "SCHEDULED",
    "ANNUAL": "SCHEDULED",
    "SER": "SCHEDULED",
    "GF": "EXTERNAL_FORCE_MAJEURE",
    "FM": "EXTERNAL_FORCE_MAJEURE",
    "GRID": "EXTERNAL_FORCE_MAJEURE",
    "EXT": "EXTERNAL_FORCE_MAJEURE",
    "E": "EXTERNAL_FORCE_MAJEURE",
    "EB": "EXTERNAL_FORCE_MAJEURE",
    "LS": "EXTERNAL_FORCE_MAJEURE",
    "BM": "FORCED_MAJOR",
    "F": "FORCED_MAJOR",
    "MAJ": "FORCED_MAJOR",
    "MAJOR": "FORCED_MAJOR",
    "BRK": "FORCED_MAJOR",
    "U": "UNSCHEDULED",
    "UNSCH": "UNSCHEDULED",
    "MIN": "UNSCHEDULED",
    "TRIP": "UNSCHEDULED",
    "GEN": "UNSCHEDULED",
}

CANONICAL_EVENT_CATEGORIES = {
    "SCHEDULED",
    "EXTERNAL_FORCE_MAJEURE",
    "FORCED_MAJOR",
    "UNSCHEDULED",
}

SCHEDULED_REMARK_PATTERN = re.compile(
    r"\b(preventive|pm|annual|routine|inspection|greasing|oil\s+sample|"
    r"overhaul|checkup|calibration|servicing)\b",
    re.IGNORECASE,
)
EXTERNAL_REMARK_PATTERN = re.compile(
    r"\b(grid|feeder|eb\s+line|line\s+outage|load\s+shedding|substation|"
    r"tripped\s+e/f|tripped\s+o/c|lightning|curtailment|grid\s+frequency)\b",
    re.IGNORECASE,
)
FORCED_MAJOR_RDS_CODES = {"MDK20", "MDE10", "MDA10"}


def normalize_event_category(category):
    if category is None:
        return None
    value = str(category).strip().upper()
    if not value:
        return None
    if value in CANONICAL_EVENT_CATEGORIES:
        return value
    return OEM_CATEGORY_SHORTHAND_MAP.get(value)


def resolve_event_category(category, rds_code, raw_remark, duration_hrs):
    normalized_category = normalize_event_category(category)
    if normalized_category:
        return normalized_category

    rds_code = str(rds_code or "").strip().upper()
    remark = str(raw_remark or "")
    if rds_code == "MXA10":
        return "EXTERNAL_FORCE_MAJEURE"
    if SCHEDULED_REMARK_PATTERN.search(remark):
        return "SCHEDULED"
    if EXTERNAL_REMARK_PATTERN.search(remark):
        return "EXTERNAL_FORCE_MAJEURE"

    try:
        duration = float(duration_hrs)
    except (TypeError, ValueError):
        duration = 0.0
    if duration >= 12.0 or rds_code in FORCED_MAJOR_RDS_CODES:
        return "FORCED_MAJOR"
    return "UNSCHEDULED"
