from django.core.management.base import BaseCommand
from django.db import transaction
from account_master.models import AccountMaster, DelinquencyStatus
from datetime import date

class Command(BaseCommand):
    help = 'Updates the delinquency status for all relevant accounts and creates a new daily snapshot.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting daily delinquency update process...'))
        today = date.today()

        # Get accounts that need their DPD updated
        accounts_to_update = AccountMaster.objects.filter(
            current_status__in=['Past Due', 'NPL']
        )

        if not accounts_to_update.exists():
            self.stdout.write(self.style.WARNING('No accounts in "Past Due" or "NPL" status. Nothing to update.'))
            return

        for account in accounts_to_update:
            # Check if a snapshot for today already exists to prevent duplicate runs
            if DelinquencyStatus.objects.filter(account=account, as_of_date=today).exists():
                self.stdout.write(f'  Skipping {account.account_id}: Snapshot for {today} already exists.')
                continue

            # --- 1. Update the AccountMaster record ---
            account.days_past_due += 1

            # Update status to NPL if it crosses the threshold
            if account.days_past_due >= 90 and account.current_status != 'NPL':
                account.current_status = 'NPL'
                if not account.npl_date:
                    account.npl_date = today
                self.stdout.write(self.style.WARNING(f'  Account {account.account_id} has been updated to NPL.'))

            account.save()

            # --- 2. Create a new DelinquencyStatus snapshot ---
            aging_bucket = None
            classification = None
            npl_flag = account.current_status == 'NPL'

            if account.days_past_due >= 360:
                aging_bucket = '360+'
                classification = 'L'
            elif account.days_past_due >= 180:
                aging_bucket = '180'
                classification = 'D'
            elif account.days_past_due >= 90:
                aging_bucket = '90'
                classification = 'SS'
            elif account.days_past_due >= 60:
                aging_bucket = '60'
                classification = 'SM'
            elif account.days_past_due >= 30:
                aging_bucket = '30'
                classification = 'SM'

            DelinquencyStatus.objects.create(
                account=account,
                as_of_date=today,
                days_past_due=account.days_past_due,
                aging_bucket=aging_bucket,
                classification=classification,
                npl_flag=npl_flag,
                npl_date=account.npl_date if npl_flag else None
            )
            self.stdout.write(f'  Created delinquency snapshot for {account.account_id} with DPD: {account.days_past_due}')

        self.stdout.write(self.style.SUCCESS('Daily delinquency update process completed successfully!'))
