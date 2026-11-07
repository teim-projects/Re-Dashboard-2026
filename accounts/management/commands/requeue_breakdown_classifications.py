import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from accounts.models import BreakdownClassificationJob


class Command(BaseCommand):
    help = (
        "Queue existing pending, review, and uncategorized breakdown rows for "
        "classification. Run once before starting the classification worker."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            help="Process only this existing breakdown table.",
        )
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument(
            "--reclassify",
            action="store_true",
            help="Re-run classification for every record, including already classified rows.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if batch_size < 1:
            raise CommandError("--batch-size must be greater than zero.")

        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            available_tables = [row[0] for row in cursor.fetchall()]

        if options["table"]:
            requested_table = options["table"]
            if not re.fullmatch(r"[a-zA-Z0-9_]+", requested_table):
                raise CommandError("Invalid table name.")
            matching_tables = [
                table for table in available_tables
                if table.lower() == requested_table.lower()
            ]
            if not matching_tables:
                raise CommandError(f"Table '{requested_table}' does not exist.")
            tables = matching_tables
        else:
            tables = [
                table for table in available_tables
                if table.lower().endswith("_breakdowndata")
            ]

        total_queued = 0
        skipped_tables = 0
        for table_name in tables:
            if not re.fullmatch(r"[a-zA-Z0-9_]+", table_name):
                continue
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                columns = {row[0].lower() for row in cursor.fetchall()}
                if not {
                    "id",
                    "rds_code",
                    "classification_status",
                }.issubset(columns):
                    skipped_tables += 1
                    continue
                if options["reclassify"]:
                    cursor.execute(
                        f"SELECT `id` FROM `{table_name}` ORDER BY `id`"
                    )
                else:
                    cursor.execute(
                        f"SELECT `id` FROM `{table_name}` "
                        "WHERE `classification_status` IN ('PENDING', 'REVIEW', 'LOW_CONFIDENCE') "
                        "OR `rds_code` = %s ORDER BY `id`",
                        ["UNCATEGORIZED"],
                    )
                while True:
                    record_ids = [row[0] for row in cursor.fetchmany(batch_size)]
                    if not record_ids:
                        break
                    now = timezone.now()
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
                        updated_at=now,
                    )
                    total_queued += len(record_ids)

        self.stdout.write(
            self.style.SUCCESS(
                f"Queued {total_queued} existing breakdown records; "
                f"skipped {skipped_tables} tables without classification fields."
            )
        )
