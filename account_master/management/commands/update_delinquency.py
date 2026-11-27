from django.core.management.base import BaseCommand
from django.db import transaction
from account_master.models import LoanAccount, DelinquencyStatus
from account_master.services.classification import (
    derive_aging_bucket,
    derive_classification,
    derive_status,
)
from datetime import date


class Command(BaseCommand):
    help = 'Updates the delinquency status for all relevant accounts and creates a new daily snapshot.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting daily delinquency update process...'))
        today = date.today()

        # Get accounts that could potentially need a DPD update.
        accounts_to_update = LoanAccount.objects.filter(
            status__in=['PAST_DUE', 'NPL']
        )

        if not accounts_to_update.exists():
            self.stdout.write(self.style.WARNING('No accounts in "PAST_DUE" or "NPL" status to update.'))
            return

        for account in accounts_to_update:
            # Prevent duplicate runs for the same day.
            if DelinquencyStatus.objects.filter(account=account, as_of_date=today).exists():
                self.stdout.write(f'  Skipping {account.loan_id}: Snapshot for {today} already exists.')
                continue

            # --- 1. Determine DPD from the latest snapshot ---
            latest_snapshot = DelinquencyStatus.objects.filter(account=account).order_by('-as_of_date').first()

            current_dpd = 0
            if latest_snapshot:
                current_dpd = latest_snapshot.days_past_due

            new_dpd = current_dpd + 1

            # --- 2. Derive classification via the shared rule (NPL starts at 91+ DPD) ---
            classification = derive_classification(new_dpd)
            npl_flag = classification in ("SS", "D", "L")
            npl_date_for_snapshot = None

            if npl_flag:
                if account.status != 'NPL':
                    # It just became NPL. Set today as the NPL date.
                    npl_date_for_snapshot = today
                else:
                    # It was already NPL, so carry over the NPL date from the previous snapshot.
                    if latest_snapshot:
                        npl_date_for_snapshot = latest_snapshot.npl_date

            # --- 3. Create a new DelinquencyStatus snapshot ---
            DelinquencyStatus.objects.create(
                account=account,
                as_of_date=today,
                days_past_due=new_dpd,
                aging_bucket=derive_aging_bucket(new_dpd),
                classification=classification,
                npl_flag=npl_flag,
                npl_date=npl_date_for_snapshot,
            )

            # --- 4. Recompute the account status via the shared rule ---
            latest_exposure = account.exposures.order_by("-as_of_date").first()
            outstanding_balance = (
                latest_exposure.principal_outstanding if latest_exposure else None
            )
            derived_status = derive_status(classification, outstanding_balance)
            if account.status != derived_status:
                account.status = derived_status
                account.save()
                if derived_status == 'NPL':
                    self.stdout.write(self.style.WARNING(
                        f'  Account {account.loan_id} status has been updated to NPL.'
                    ))

            self.stdout.write(f'  Created delinquency snapshot for {account.loan_id} with DPD: {new_dpd}')

        self.stdout.write(self.style.SUCCESS('Daily delinquency update process completed successfully!'))
