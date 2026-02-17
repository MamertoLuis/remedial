from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from account_master.models import LoanAccount, Borrower


class Command(BaseCommand):
    help = 'Load all dummy data including accounts, exposures, delinquencies, etc.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to load all dummy data...'))

        # First, load borrowers and accounts
        self.stdout.write(self.style.SUCCESS('Loading borrowers and loan accounts...'))
        dummy_borrowers = [
            {'borrower_id': 'BRW001', 'full_name': 'John Smith', 'borrower_type': 'PERSON', 'mobile': '123-456-7890', 'email': 'john.smith@example.com', 'primary_address': '123 Main St'},
            {'borrower_id': 'BRW002', 'full_name': 'Jane Doe', 'borrower_type': 'PERSON', 'mobile': '234-567-8901', 'email': 'jane.doe@example.com', 'primary_address': '456 Oak Ave'},
            {'borrower_id': 'BRW003', 'full_name': 'Michael Brown', 'borrower_type': 'PERSON', 'mobile': '345-678-9012', 'email': 'michael.brown@example.com', 'primary_address': '789 Pine Ln'},
            {'borrower_id': 'BRW004', 'full_name': 'Sarah Johnson', 'borrower_type': 'PERSON', 'mobile': '456-789-0123', 'email': 'sarah.johnson@example.com', 'primary_address': '101 Maple Dr'},
            {'borrower_id': 'BRW005', 'full_name': 'David Miller', 'borrower_type': 'PERSON', 'mobile': '567-890-1234', 'email': 'david.miller@example.com', 'primary_address': '212 Birch Rd'},
            {'borrower_id': 'BRW006', 'full_name': 'Emma Wilson', 'borrower_type': 'PERSON', 'mobile': '678-901-2345', 'email': 'emma.wilson@example.com', 'primary_address': '333 Cedar Ct'},
            {'borrower_id': 'BRW007', 'full_name': 'Robert Taylor', 'borrower_type': 'PERSON', 'mobile': '789-012-3456', 'email': 'robert.taylor@example.com', 'primary_address': '444 Elm St'},
            {'borrower_id': 'BRW008', 'full_name': 'Lisa Anderson', 'borrower_type': 'PERSON', 'mobile': '890-123-4567', 'email': 'lisa.anderson@example.com', 'primary_address': '555 Spruce Ave'},
            {'borrower_id': 'BRW009', 'full_name': 'James Martin', 'borrower_type': 'PERSON', 'mobile': '901-234-5678', 'email': 'james.martin@example.com', 'primary_address': '666 Willow Ln'},
            {'borrower_id': 'BRW010', 'full_name': 'Patricia Lewis', 'borrower_type': 'PERSON', 'mobile': '012-345-6789', 'email': 'patricia.lewis@example.com', 'primary_address': '777 Aspen Dr'},
        ]

        for borrower_data in dummy_borrowers:
            borrower, created = Borrower.objects.get_or_create(
                borrower_id=borrower_data['borrower_id'],
                defaults=borrower_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created borrower {borrower_data['borrower_id']}"))
            else:
                self.stdout.write(self.style.WARNING(f"  Borrower {borrower_data['borrower_id']} already exists"))

        dummy_accounts = [
            {
                'loan_id': 'ACC001',
                'borrower_id': 'BRW001',
                'pn_number': 'PN001',
                'loan_type': 'Home Loan',
                'booking_date': timezone.now().date() - timedelta(days=365),
                'original_principal': Decimal('500000.00'),
                'interest_rate': Decimal('5.50'),
                'maturity_date': timezone.now().date() + timedelta(days=3650),
                'branch_code': 'BR001',
                'account_officer_id': 'AO001',
                'status': 'PERFORMING',
            },
            {
                'loan_id': 'ACC002',
                'borrower_id': 'BRW002',
                'pn_number': 'PN002',
                'loan_type': 'Personal Loan',
                'booking_date': timezone.now().date() - timedelta(days=180),
                'original_principal': Decimal('100000.00'),
                'interest_rate': Decimal('8.25'),
                'maturity_date': timezone.now().date() + timedelta(days=1800),
                'branch_code': 'BR002',
                'account_officer_id': 'AO002',
                'status': 'PERFORMING',
            },
            {
                'loan_id': 'ACC003',
                'borrower_id': 'BRW003',
                'pn_number': 'PN003',
                'loan_type': 'Auto Loan',
                'booking_date': timezone.now().date() - timedelta(days=90),
                'original_principal': Decimal('35000.00'),
                'interest_rate': Decimal('4.75'),
                'maturity_date': timezone.now().date() + timedelta(days=1800),
                'branch_code': 'BR001',
                'account_officer_id': 'AO001',
                'status': 'PERFORMING',
            },
            {
                'loan_id': 'ACC004',
                'borrower_id': 'BRW004',
                'pn_number': 'PN004',
                'loan_type': 'Business Loan',
                'booking_date': timezone.now().date() - timedelta(days=270),
                'original_principal': Decimal('250000.00'),
                'interest_rate': Decimal('7.00'),
                'maturity_date': timezone.now().date() + timedelta(days=2700),
                'branch_code': 'BR003',
                'account_officer_id': 'AO003',
                'status': 'PAST_DUE',
            },
            {
                'loan_id': 'ACC005',
                'borrower_id': 'BRW005',
                'pn_number': 'PN005',
                'loan_type': 'Home Loan',
                'booking_date': timezone.now().date() - timedelta(days=450),
                'original_principal': Decimal('600000.00'),
                'interest_rate': Decimal('6.00'),
                'maturity_date': timezone.now().date() + timedelta(days=3000),
                'branch_code': 'BR002',
                'account_officer_id': 'AO002',
                'status': 'PERFORMING',
            },
            {
                'loan_id': 'ACC006',
                'borrower_id': 'BRW006',
                'pn_number': 'PN006',
                'loan_type': 'Education Loan',
                'booking_date': timezone.now().date() - timedelta(days=365),
                'original_principal': Decimal('150000.00'),
                'interest_rate': Decimal('3.50'),
                'maturity_date': timezone.now().date() + timedelta(days=5400),
                'branch_code': 'BR001',
                'account_officer_id': 'AO001',
                'status': 'PERFORMING',
            },
            {
                'loan_id': 'ACC007',
                'borrower_id': 'BRW007',
                'pn_number': 'PN007',
                'loan_type': 'Personal Loan',
                'booking_date': timezone.now().date() - timedelta(days=200),
                'original_principal': Decimal('50000.00'),
                'interest_rate': Decimal('9.00'),
                'maturity_date': timezone.now().date() + timedelta(days=1000),
                'branch_code': 'BR003',
                'account_officer_id': 'AO003',
                'status': 'NPL',
            },
            {
                'loan_id': 'ACC008',
                'borrower_id': 'BRW008',
                'pn_number': 'PN008',
                'loan_type': 'Auto Loan',
                'booking_date': timezone.now().date() - timedelta(days=120),
                'original_principal': Decimal('45000.00'),
                'interest_rate': Decimal('5.25'),
                'maturity_date': timezone.now().date() + timedelta(days=1500),
                'branch_code': 'BR002',
                'account_officer_id': 'AO002',
                'status': 'PERFORMING',
            },
            {
                'loan_id': 'ACC009',
                'borrower_id': 'BRW009',
                'pn_number': 'PN009',
                'loan_type': 'Home Loan',
                'booking_date': timezone.now().date() - timedelta(days=300),
                'original_principal': Decimal('550000.00'),
                'interest_rate': Decimal('5.75'),
                'maturity_date': timezone.now().date() + timedelta(days=3000),
                'branch_code': 'BR001',
                'account_officer_id': 'AO001',
                'status': 'PAST_DUE',
            },
            {
                'loan_id': 'ACC010',
                'borrower_id': 'BRW010',
                'pn_number': 'PN010',
                'loan_type': 'Business Loan',
                'booking_date': timezone.now().date() - timedelta(days=400),
                'original_principal': Decimal('300000.00'),
                'interest_rate': Decimal('7.50'),
                'maturity_date': timezone.now().date() + timedelta(days=2400),
                'branch_code': 'BR003',
                'account_officer_id': 'AO003',
                'status': 'WRITEOFF',
            },
        ]

        for data in dummy_accounts:
            borrower_id = data.pop('borrower_id')
            borrower = Borrower.objects.get(borrower_id=borrower_id)
            account, created = LoanAccount.objects.get_or_create(
                loan_id=data['loan_id'],
                defaults={**data, 'borrower': borrower}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created account {data['loan_id']}"))
            else:
                self.stdout.write(self.style.WARNING(f"  Account {data['loan_id']} already exists"))

        self.stdout.write(self.style.SUCCESS('Successfully loaded borrowers and accounts.'))

        # Call other dummy data loaders
        self.stdout.write(self.style.SUCCESS('\nLoading other related dummy data...'))
        call_command('load_dummy_exposure')
        call_command('load_dummy_delinquency')
        call_command('load_dummy_collection_activities')
        call_command('load_dummy_remedial_strategies')
        call_command('load_dummy_compromise')

        self.stdout.write(self.style.SUCCESS('\nAll dummy data has been loaded successfully!'))
