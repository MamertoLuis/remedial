"""Import borrower master data under the csv-import contract.

The whole file is validated (exact headers, strict types, within-file
uniqueness) before any row is written; nothing is written when any row is
invalid and the command exits non-zero. See ``specs/csv-import/spec.md``.
"""

from django.core.management.base import BaseCommand

from account_master.services import csv_import


class Command(BaseCommand):
    help = (
        "Import borrower master data from a CSV file under the csv-import "
        "contract (whole-file validation, no silent coercion)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip updating existing borrowers (only create new ones).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report what would be imported without writing rows.",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]

        verb = "DRY RUN: would import" if dry_run else "Imported"
        self.stdout.write(
            self.style.SUCCESS(f"Attempting to import borrower data from {csv_file}...")
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no rows will be written."))

        summary = csv_import.import_borrowers_file(
            csv_file, dry_run=dry_run, skip_existing=skip_existing
        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{verb} {summary.created} new borrowers and update "
                    f"{summary.updated} existing borrowers."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {summary.created} new borrowers, "
                    f"updated {summary.updated} existing borrowers, and skipped "
                    f"{summary.skipped} existing borrowers."
                )
            )