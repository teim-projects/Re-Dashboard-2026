import hashlib
import json
import re
import unicodedata

import pandas as pd
from django.db import connection, transaction
from django.utils import timezone

from accounts.breakdown_mapping import REQUIRED_BREAKDOWN_FIELDS
from accounts.models import BreakdownClassificationJob


FINGERPRINT_FIELDS = (
    "provider_id",
    "site",
    "gen_date",
    "loc_no",
    "breakdown_remarks",
    "start_time",
    "end_time",
    "duration_hrs",
    "event_category",
)

BREAKDOWN_STORAGE_COLUMNS = {
    "state": "`state` VARCHAR(100) NULL",
    "rds_code": "`rds_code` VARCHAR(50) NOT NULL DEFAULT 'UNCATEGORIZED'",
    "system_name": "`system_name` VARCHAR(150) NOT NULL DEFAULT 'General Maintenance'",
    "standard_component": "`standard_component` VARCHAR(150) NOT NULL DEFAULT 'Unmapped Remark'",
    "classification_status": "`classification_status` VARCHAR(16) NOT NULL DEFAULT 'PENDING'",
    "classification_confidence": "`classification_confidence` FLOAT NULL",
    "classification_processed_at": "`classification_processed_at` DATETIME NULL",
    "record_fingerprint": "`record_fingerprint` CHAR(64) NULL",
}


def _normalize_fingerprint_value(value):
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str):
        return " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    return str(value)


def breakdown_record_fingerprint(record):
    payload = {
        field: _normalize_fingerprint_value(record.get(field))
        for field in FINGERPRINT_FIELDS
    }
    if not any(value is not None for value in payload.values()):
        payload["legacy_row_id"] = record.get("id")
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def deduplicate_breakdown_dataframe(dataframe):
    rows = dataframe.copy()
    rows["record_fingerprint"] = rows.apply(
        lambda row: breakdown_record_fingerprint(row.to_dict()),
        axis=1,
    )
    before = len(rows)
    rows = rows.drop_duplicates(subset=["record_fingerprint"], keep="first")
    return rows, before - len(rows)


def enqueue_breakdown_classification_jobs(table_name, record_ids):
    if not record_ids:
        return

    BreakdownClassificationJob.objects.bulk_create(
        [
            BreakdownClassificationJob(
                table_name=table_name,
                record_id=record_id,
            )
            for record_id in record_ids
        ],
        ignore_conflicts=True,
    )
    BreakdownClassificationJob.objects.filter(
        table_name=table_name,
        record_id__in=record_ids,
    ).update(
        status=BreakdownClassificationJob.Status.PENDING,
        attempts=0,
        last_error="",
        updated_at=timezone.now(),
    )


def ensure_breakdown_deduplication(table_name):
    if not re.fullmatch(r"[a-zA-Z0-9_]+", table_name):
        raise ValueError("Invalid breakdown table name.")

    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        existing_columns = {row[0].lower() for row in cursor.fetchall()}
        for column_name, definition in BREAKDOWN_STORAGE_COLUMNS.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE `{table_name}` ADD COLUMN {definition}"
                )
                existing_columns.add(column_name)

        cursor.execute(f"SHOW INDEX FROM `{table_name}`")
        has_unique_fingerprint = any(
            row[2] == 0 and row[4] == "record_fingerprint"
            for row in cursor.fetchall()
        )
        if has_unique_fingerprint:
            return

        fingerprint_columns = [
            field
            for field in FINGERPRINT_FIELDS
            if field in existing_columns
        ]
        select_columns = ["id", *fingerprint_columns, "record_fingerprint"]
        cursor.execute(
            f"SELECT {', '.join(f'`{column}`' for column in select_columns)} "
            f"FROM `{table_name}` ORDER BY `id`"
        )
        rows = cursor.fetchall()
        seen_fingerprints = set()
        duplicate_ids = []
        updates = []
        for row in rows:
            record = dict(zip(select_columns, row))
            fingerprint = breakdown_record_fingerprint(record)
            if fingerprint in seen_fingerprints:
                duplicate_ids.append(record["id"])
            else:
                seen_fingerprints.add(fingerprint)
                updates.append((fingerprint, record["id"]))

        if updates:
            cursor.executemany(
                f"UPDATE `{table_name}` SET `record_fingerprint` = %s WHERE `id` = %s",
                updates,
            )
        if duplicate_ids:
            placeholders = ", ".join(["%s"] * len(duplicate_ids))
            cursor.execute(
                f"DELETE FROM `{table_name}` WHERE `id` IN ({placeholders})",
                duplicate_ids,
            )
        cursor.execute(
            f"CREATE UNIQUE INDEX `uq_record_fingerprint` "
            f"ON `{table_name}` (`record_fingerprint`)"
        )


def insert_canonical_breakdown_rows(table_name, dataframe):
    if dataframe.empty:
        return 0, 0

    missing_fields = REQUIRED_BREAKDOWN_FIELDS - set(dataframe.columns)
    if missing_fields:
        raise ValueError(
            "Canonical breakdown rows are missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    ensure_breakdown_deduplication(table_name)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            table_columns = {row[0].lower() for row in cursor.fetchall()}

        rows, duplicate_count = deduplicate_breakdown_dataframe(dataframe)
        final_columns = [
            column for column in rows.columns
            if column.lower() in table_columns
        ]
        if "record_fingerprint" not in final_columns:
            raise RuntimeError(
                f"Breakdown table '{table_name}' does not contain record_fingerprint."
            )

        inserted_ids = []
        columns_sql = ", ".join(f"`{column}`" for column in final_columns)
        placeholders = ", ".join(["%s"] * len(final_columns))
        insert_sql = (
            f"INSERT INTO `{table_name}` ({columns_sql}) "
            f"VALUES ({placeholders}) "
            "ON DUPLICATE KEY UPDATE `record_fingerprint` = `record_fingerprint`"
        )
        with connection.cursor() as cursor:
            for row in rows[final_columns].itertuples(index=False, name=None):
                values = tuple(
                    None if pd.isna(value) else value
                    for value in row
                )
                cursor.execute(insert_sql, values)
                if cursor.rowcount == 1:
                    inserted_ids.append(cursor.lastrowid)

        if inserted_ids:
            enqueue_breakdown_classification_jobs(table_name, inserted_ids)

    return len(inserted_ids), duplicate_count + len(rows) - len(inserted_ids)
