from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from account_master.models import AccountMaster, Borrower


class Command(BaseCommand):
    help = 'Load 10 dummy AccountMaster records'

    def handle(self, *args, **options):
        dummy_borrowers = [
            {'borrower_id': 'BRW001', 'first_name': 'John', 'last_name': 'Smith', 'phone_number': '123-456-7890', 'email': 'john.smith@example.com', 'address': '123 Main St'},
            {'borrower_id': 'BRW002', 'first_name': 'Jane', 'last_name': 'Doe', 'phone_number': '234-567-8901', 'email': 'jane.doe@example.com', 'address': '456 Oak Ave'},
            {'borrower_id': 'BRW003', 'first_name': 'Michael', 'last_name': 'Brown', 'phone_number': '345-678-9012', 'email': 'michael.brown@example.com', 'address': '789 Pine Ln'},
            {'borrower_id': 'BRW004', 'first_name': 'Sarah', 'last_name': 'Johnson', 'phone_number': '456-789-0123', 'email': 'sarah.johnson@example.com', 'address': '101 Maple Dr'},
            {'borrower_id': 'BRW005', 'first_name': 'David', 'last_name': 'Miller', 'phone_number': '567-890-1234', 'email': 'david.miller@example.com', 'address': '212 Birch Rd'},
            {'borrower_id': 'BRW006', 'first_name': 'Emma', 'last_name': 'Wilson', 'phone_number': '678-901-2345', 'email': 'emma.wilson@example.com', 'address': '333 Cedar Ct'},
            {'borrower_id': 'BRW007', 'first_name': 'Robert', 'last_name': 'Taylor', 'phone_number': '789-012-3456', 'email': 'robert.taylor@example.com', 'address': '444 Elm St'},
            {'borrower_id': 'BRW008', 'first_name': 'Lisa', 'last_name': 'Anderson', 'phone_number': '890-123-4567', 'email': 'lisa.anderson@example.com', 'address': '555 Spruce Ave'},
            {'borrower_id': 'BRW009', 'first_name': 'James', 'last_name': 'Martin', 'phone_number': '901-234-5678', 'email': 'james.martin@example.com', 'address': '666 Willow Ln'},
            {'borrower_id': 'BRW010', 'first_name': 'Patricia', 'last_name': 'Lewis', 'phone_number': '012-345-6789', 'email': 'patricia.lewis@example.com', 'address': '777 Aspen Dr'},
        ]

        for borrower_data in dummy_borrowers:
            borrower, created = Borrower.objects.get_or_create(
                borrower_id=borrower_data['borrower_id'],
                defaults=borrower_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created borrower {borrower_data['borrower_id']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Borrower {borrower_data['borrower_id']} already exists"))

        dummy_accounts = [
            {
                'account_id': 'ACC001',
                'borrower_id': 'BRW001',
                'loan_type': 'Home Loan',
                'booking_date': timezone.now().date() - timedelta(days=365),
                'original_principal': Decimal('500000.00'),
                'interest_rate': Decimal('5.50'),
                'maturity_date': timezone.now().date() + timedelta(days=3650),
                'branch_code': 'BR001',
                'account_officer': 'Alice Johnson',
                'security_type': 'REM',
                'current_status': 'Performing',
                'days_past_due': 0,
            },
            {
                'account_id': 'ACC002',
                'borrower_id': 'BRW002',
                'loan_type': 'Personal Loan',
                'booking_date': timezone.now().date() - timedelta(days=180),
                'original_principal': Decimal('100000.00'),
                'interest_rate': Decimal('8.25'),
                'maturity_date': timezone.now().date() + timedelta(days=1800),
                'branch_code': 'BR002',
                'account_officer': 'Bob Wilson',
                'security_type': 'Unsecured',
                'current_status': 'Performing',
                'days_past_due': 0,
            },
            {
                'account_id': 'ACC003',
                'borrower_id': 'BRW003',
                'loan_type': 'Auto Loan',
                'booking_date': timezone.now().date() - timedelta(days=90),
                'original_principal': Decimal('35000.00'),
                'interest_rate': Decimal('4.75'),
                'maturity_date': timezone.now().date() + timedelta(days=1800),
                'branch_code': 'BR001',
                'account_officer': 'Alice Johnson',
                'security_type': 'CM',
                'current_status': 'Performing',
                'days_past_due': 0,
            },
            {
                'account_id': 'ACC004',
                'borrower_id': 'BRW004',
                'loan_type': 'Business Loan',
                'booking_date': timezone.now().date() - timedelta(days=270),
                'original_principal': Decimal('250000.00'),
                'interest_rate': Decimal('7.00'),
                'maturity_date': timezone.now().date() + timedelta(days=2700),
                'branch_code': 'BR003',
                'account_officer': 'Carol Davis',
                'security_type': 'Mixed',
                'current_status': 'Past Due',
                'days_past_due': 45,
            },
            {
                'account_id': 'ACC005',
                'borrower_id': 'BRW005',
                'loan_type': 'Home Loan',
                'booking_date': timezone.now().date() - timedelta(days=450),
                'original_principal': Decimal('600000.00'),
                'interest_rate': Decimal('6.00'),
                'maturity_date': timezone.now().date() + timedelta(days=3000),
                'branch_code': 'BR002',
                'account_officer': 'Bob Wilson',
                'security_type': 'REM',
                'current_status': 'Performing',
                'days_past_due': 0,
            },
            {
                'account_id': 'ACC006',
                'borrower_id': 'BRW006',
                'loan_type': 'Education Loan',
                'booking_date': timezone.now().date() - timedelta(days=365),
                'original_principal': Decimal('150000.00'),
                'interest_rate': Decimal('3.50'),
                'maturity_date': timezone.now().date() + timedelta(days=5400),
                'branch_code': 'BR001',
                'account_officer': 'Alice Johnson',
                'security_type': 'Unsecured',
                'current_status': 'Performing',
                'days_past_due': 0,
            },
            {
                'account_id': 'ACC007',
                'borrower_id': 'BRW007',
                'loan_type': 'Personal Loan',
                'booking_date': timezone.now().date() - timedelta(days=200),
                'original_principal': Decimal('50000.00'),
                'interest_rate': Decimal('9.00'),
                'maturity_date': timezone.now().date() + timedelta(days=1000),
                'branch_code': 'BR003',
                'account_officer': 'Carol Davis',
                'security_type': 'Unsecured',
                'current_status': 'NPL',
                'days_past_due': 180,
            },
            {
                'account_id': 'ACC008',
                'borrower_id': 'BRW008',
                'loan_type': 'Auto Loan',
                'booking_date': timezone.now().date() - timedelta(days=120),
                'original_principal': Decimal('45000.00'),
                'interest_rate': Decimal('5.25'),
                'maturity_date': timezone.now().date() + timedelta(days=1500),
                'branch_code': 'BR002',
                'account_officer': 'Bob Wilson',
                'security_type': 'CM',
                'current_status': 'Performing',
                'days_past_due': 0,
            },
            {
                'account_id': 'ACC009',
                'borrower_id': 'BRW009',
                'loan_type': 'Home Loan',
                'booking_date': timezone.now().date() - timedelta(days=300),
                'original_principal': Decimal('550000.00'),
                'interest_rate': Decimal('5.75'),
                'maturity_date': timezone.now().date() + timedelta(days=3000),
                'branch_code': 'BR001',
                'account_officer': 'Alice Johnson',
                'security_type': 'REM',
                'current_status': 'Past Due',
                'days_past_due': 30,
            },
            {
                'account_id': 'ACC010',
                'borrower_id': 'BRW010',
                'loan_type': 'Business Loan',
                'booking_date': timezone.now().date() - timedelta(days=400),
                'original_principal': Decimal('300000.00'),
                'interest_rate': Decimal('7.50'),
                'maturity_date': timezone.now().date() + timedelta(days=2400),
                'branch_code': 'BR003',
                'account_officer': 'Carol Davis',
                'security_type': 'Mixed',
                'current_status': 'Written-Off',
                'days_past_due': 365,
            },
        ]

        for data in dummy_accounts:
            borrower_id = data.pop('borrower_id')
            borrower = Borrower.objects.get(borrower_id=borrower_id)
            account, created = AccountMaster.objects.get_or_create(
                account_id=data['account_id'],
                defaults={**data, 'borrower': borrower}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created account {data['account_id']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Account {data['account_id']} already exists"))

        self.stdout.write(self.style.SUCCESS('Successfully loaded dummy data'))
