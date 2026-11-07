import time

from django.core.management.base import BaseCommand, CommandError

from accounts.breakdown_classification import process_classification_batch


class Command(BaseCommand):
    help = (
        "Process queued breakdown remarks and map them to the RDS catalog. "
        "Run continuously as a background worker; --once processes one batch."
    )

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--poll-seconds", type=float, default=5)

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        poll_seconds = options["poll_seconds"]
        if batch_size < 1:
            raise CommandError("--batch-size must be greater than zero.")
        if poll_seconds <= 0:
            raise CommandError("--poll-seconds must be greater than zero.")

        while True:
            counts = process_classification_batch(batch_size=batch_size)
            if counts["claimed"]:
                self.stdout.write(
                    "Processed {claimed}: {classified} classified, "
                    "{low_confidence} assigned with low confidence, "
                    "{failed} failed.".format(**counts)
                )
            elif options["once"]:
                self.stdout.write("No pending breakdown classification jobs.")

            if options["once"]:
                break
            if not counts["claimed"]:
                time.sleep(poll_seconds)
