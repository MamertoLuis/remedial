"""Single-hop data refresh from the iAccs core-banking MySQL database.

Reads loan masters, balances and repayment schedules directly from the iAccs
MySQL source (read-only) and upserts ``Borrower`` / ``LoanAccount`` /
``Exposure`` through the existing service layer, so the existing derivation
cascade (delinquency -> account status -> rule-based ECL) runs unchanged.

Semantic note: ``days_past_due`` is *computed* here from the repayment
schedule (aggregate-shortfall rule) rather than read from a stored value or
an external CSV, so values may differ from the schedule of a file-based
import even when the underlying data is unchanged.
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from account_master.services.iaccs import connection
from account_master.services.iaccs.loader import sync_from_iaccs


class Command(BaseCommand):
    help = (
        "Import borrower, loan-account and exposure data directly from the "
        "iAccs core-banking MySQL database (read-only)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--cutoff",
            required=True,
            help="As-of date for the snapshot, formatted YYYY-MM-DD.",
        )
        parser.add_argument(
            "--branch",
            type=int,
            default=None,
            help="Branch code to import (default: all live branches).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be imported without writing any rows.",
        )

    def handle(self, *args, **options):
        cutoff = self._parse_cutoff(options["cutoff"])
        dry_run = options["dry_run"]
        branch = options["branch"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no rows will be written."))

        try:
            conn = connection.get_connection()
        except Exception as exc:  # noqa: BLE001 - surface any connection error
            raise CommandError(
                f"Could not connect to the iAccs MySQL database: {exc}"
            )

        try:
            summary = sync_from_iaccs(conn, branch, cutoff, dry_run=dry_run)
        finally:
            conn.close()

        self._print_summary(summary, dry_run=dry_run)

        if summary["errors"]:
            for error in summary["errors"]:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError(
                f"Finished with {len(summary['errors'])} errors. "
                "See above for details."
            )

    def _parse_cutoff(self, raw: str) -> date:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            raise CommandError("--cutoff must be a valid date in YYYY-MM-DD format.")

    def _print_summary(self, summary: dict, dry_run: bool) -> None:
        verb = "Would import" if dry_run else "Imported"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {summary['borrowers_created']} new borrowers, "
                f"{summary['borrowers_updated']} updated borrowers; "
                f"{summary['accounts_created']} new accounts, "
                f"{summary['accounts_updated']} updated accounts; "
                f"{summary['exposures_created']} new exposures, "
                f"{summary['exposures_updated']} updated exposures "
                f"across {summary['loans']} loans."
            )
        )