"""Repair legacy-written delinquency rows at exactly 90 days past due.

The corrected NPL boundary is *more than 90 days* (91+): a loan with exactly
90 days past due is classified ``SM`` (status ``PAST_DUE``), not NPL. The
current iAccs pipeline never wrote 90-day rows as ``SS``, but the legacy
commands (``update_delinquency``, ``load_dummy_delinquency``) did, because
they used a >= 90 boundary. This command is a safety net that repairs any
such rows:

- ``DelinquencyStatus`` rows with ``days_past_due == 90`` and
  ``classification == "SS"`` are reset to ``SM`` / ``npl_flag`` false
  (and their ``npl_date`` cleared, since the snapshot is no longer NPL).
- The affected accounts' ``LoanAccount.status`` is recomputed via the shared
  ``derive_status`` rule (preserving the WRITEOFF/CLOSED sentinels).
- The dashboard cache is cleared so KPIs reflect the repair immediately.

Run with ``--dry-run`` to report affected rows without changing anything.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from account_master.models import DelinquencyStatus, LoanAccount
from account_master.services.classification import derive_status
from account_master.services.dashboard_service import DashboardService


class Command(BaseCommand):
    help = (
        "Repair legacy-written DelinquencyStatus rows at exactly 90 days past "
        "due (classification SS -> SM, npl_flag false)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report affected rows without changing anything.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        rows = DelinquencyStatus.objects.filter(
            days_past_due=90, classification="SS"
        )
        affected_account_ids = set(rows.values_list("account_id", flat=True))
        self.stdout.write(
            f"Found {rows.count()} legacy 90-DPD SS row(s) across "
            f"{len(affected_account_ids)} account(s)."
        )

        if dry_run:
            self.stdout.write("Dry run - no changes made.")
            return

        if rows.exists():
            updated = rows.update(classification="SM", npl_flag=False, npl_date=None)
        else:
            updated = 0

        # Recompute status for every affected account (WRITEOFF/CLOSED sentinels
        # preserved via the shared derive_status rule).
        for account in LoanAccount.objects.filter(pk__in=affected_account_ids):
            latest = account.delinquency_statuses.order_by("-as_of_date").first()
            latest_exposure = account.exposures.order_by("-as_of_date").first()
            outstanding = (
                latest_exposure.principal_outstanding if latest_exposure else None
            )
            classification = latest.classification if latest else "C"
            derived_status = derive_status(classification, outstanding)
            if account.status != derived_status:
                account.status = derived_status
                account.save(update_fields=["status", "updated_at"])

        DashboardService.clear_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f"Repaired {updated} row(s); dashboard cache cleared."
            )
        )
