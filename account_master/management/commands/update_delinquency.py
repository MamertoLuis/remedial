from django.core.management.base import BaseCommand
from django.db import transaction
from account_master.models import LoanAccount, DelinquencyStatus
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

            # --- 2. Update LoanAccount status and determine NPL date for the new snapshot ---
            npl_flag = False
            npl_date_for_snapshot = None

            if new_dpd >= 90:
                npl_flag = True
                if account.status != 'NPL':
                    # It just became NPL. Update the main account status and set today as the NPL date.
                    account.status = 'NPL'
                    account.save()
                    npl_date_for_snapshot = today
                    self.stdout.write(self.style.WARNING(f'  Account {account.loan_id} status has been updated to NPL.'))
                else:
                    # It was already NPL, so carry over the NPL date from the previous snapshot.
                    if latest_snapshot:
                        npl_date_for_snapshot = latest_snapshot.npl_date
            
            # --- 3. Create a new DelinquencyStatus snapshot ---
            aging_bucket = 'Current'
            classification = 'C'

            if new_dpd >= 360:
                aging_bucket = '360+'
                classification = 'L'
            elif new_dpd >= 180:
                aging_bucket = '180'
                classification = 'D'
            elif new_dpd >= 90:
                aging_bucket = '90'
                classification = 'SS'
            elif new_dpd >= 60:
                aging_bucket = '60'
                classification = 'SM'
            elif new_dpd >= 30:
                aging_bucket = '30'
                classification = 'SM'

            DelinquencyStatus.objects.create(
                account=account,
                as_of_date=today,
                days_past_due=new_dpd,
                aging_bucket=aging_bucket,
                classification=classification,
                npl_flag=npl_flag,
                npl_date=npl_date_for_snapshot
            )
            self.stdout.write(f'  Created delinquency snapshot for {account.loan_id} with DPD: {new_dpd}')

        self.stdout.write(self.style.SUCCESS('Daily delinquency update process completed successfully!'))
