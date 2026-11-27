"""Import exposure observations under the csv-import contract.

Accepts only observation columns; ``days_past_due`` is never read from the
file — it is computed from the iAccs repayment schedule through the same
read-only connection and rule as the bulk iaccs import. The whole file is
validated (headers, types, referential integrity, within-file uniqueness,
iAccs-provenance conflicts) before any row is written. See
``specs/csv-import/spec.md``.
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from account_master.services import csv_import
from account_master.services.iaccs import connection


class Command(BaseCommand):
    help = (
        "Import exposure observations from a CSV file under the csv-import "
        "contract; days past due is computed from the iAccs repayment schedule."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )
        parser.add_argument(
            "--cutoff",
            required=True,
            help="As-of date for the snapshot, formatted YYYY-MM-DD.",
        )
        parser.add_argument(
            "--snapshot-type",
            type=str,
            choices=["EVENT", "MONTH_END"],
            default="EVENT",
            help="Snapshot type stored on the exposure row (EVENT or MONTH_END).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report what would be imported without writing rows.",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        snapshot_type = options["snapshot_type"]
        dry_run = options["dry_run"]

        try:
            cutoff = date.fromisoformat(options["cutoff"])
        except ValueError:
            raise CommandError("--cutoff must be a valid date in YYYY-MM-DD format.")

        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import exposure data from {csv_file}..."
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no rows will be written."))

        try:
            conn = connection.get_connection()
        except Exception as exc:  # noqa: BLE001 - surface any connection error
            raise CommandError(
                f"Could not connect to the iAccs MySQL database: {exc}"
            )

        try:
            summary = csv_import.import_exposures_file(
                csv_file,
                dry_run=dry_run,
                snapshot_type=snapshot_type,
                conn=conn,
                cutoff=cutoff,
            )
        finally:
            conn.close()

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: would import {summary.created} new exposure records "
                    f"and update {summary.updated} existing records."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {summary.created} new exposure records "
                    f"and updated {summary.updated} existing records."
                )
            )