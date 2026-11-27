"""Import loan account master data under the csv-import contract.

The whole file is validated (exact headers, strict types, referential
integrity, within-file uniqueness) before any row is written; nothing is
written when any row is invalid and the command exits non-zero. Account
``status`` is always derived and rejected from files; ``loan_security`` is
required per row. See ``specs/csv-import/spec.md``.
"""

from django.core.management.base import BaseCommand

from account_master.services import csv_import


class Command(BaseCommand):
    help = (
        "Import loan account master data from a CSV file under the csv-import "
        "contract (status is derived, loan_security is required)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report what would be imported without writing rows.",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip updating existing loan accounts (only create new ones).",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        skip_existing = options["skip_existing"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import loan account data from {csv_file}..."
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no rows will be written."))

        summary = csv_import.import_accounts_file(
            csv_file, dry_run=dry_run, skip_existing=skip_existing
        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: would import {summary.created} new loan accounts "
                    f"and update {summary.updated} existing accounts."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {summary.created} new loan accounts, "
                    f"updated {summary.updated} existing accounts, and skipped "
                    f"{summary.skipped} existing accounts."
                )
            )