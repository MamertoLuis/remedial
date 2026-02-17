from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from account_master.models import LoanAccount
from account_master.services import take_snapshot

class Command(BaseCommand):
    help = 'Tests the take_snapshot service.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Testing take_snapshot service ---'))

        # Get a sample loan account
        try:
            account = LoanAccount.objects.get(loan_id='L0001')
        except LoanAccount.DoesNotExist:
            raise CommandError("LoanAccount with loan_id='L0001' does not exist. Please create it first.")

        as_of_date = datetime.strptime('2024-01-31', '%Y-%m-%d').date()

        exposure_data = {
            'principal_outstanding': Decimal('450000.00'),
            'accrued_interest': Decimal('1200.00'),
            'accrued_penalty': Decimal('0.00'),
        }

        delinquency_data = {
            'days_past_due': 0,
            'aging_bucket': None,
            'classification': None,
            'npl_flag': False,
        }

        try:
            take_snapshot(
                account=account,
                as_of_date=as_of_date,
                exposure_data=exposure_data,
                delinquency_data=delinquency_data,
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created snapshot for account {account.loan_id} on {as_of_date}.'))
        except Exception as e:
            raise CommandError(f'An error occurred during snapshot creation: {e}')
