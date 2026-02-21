from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from account_master.models import LoanAccount, Borrower
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Load foundational dummy data (borrowers and loan accounts only)."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Starting to load foundational dummy data...")
        )

        # Create or get dummy user for audit fields
        user, created = User.objects.get_or_create(
            username="dummy_user", defaults={"email": "dummy@example.com"}
        )
        if created:
            user.set_password("dummy_password")
            user.save()
            self.stdout.write(f"Created dummy user: {user.username}")

        # Load borrowers
        self.stdout.write(self.style.SUCCESS("Loading borrowers..."))
        dummy_borrowers = [
            {
                "borrower_id": "BRW001",
                "full_name": "John Smith",
                "borrower_type": "PERSON",
                "mobile": "0917-123-4567",
                "primary_address": "123 Main Street, Makati City",
            },
            {
                "borrower_id": "BRW002",
                "full_name": "Jane Doe",
                "borrower_type": "PERSON",
                "mobile": "0917-234-5678",
                "primary_address": "456 Oak Avenue, Quezon City",
            },
            {
                "borrower_id": "BRW003",
                "full_name": "Michael Brown",
                "borrower_type": "PERSON",
                "mobile": "0917-345-6789",
                "primary_address": "789 Pine Lane, Mandaluyong City",
            },
            {
                "borrower_id": "BRW004",
                "full_name": "Sarah Johnson",
                "borrower_type": "PERSON",
                "mobile": "0917-456-7890",
                "primary_address": "101 Maple Drive, San Juan City",
            },
            {
                "borrower_id": "BRW005",
                "full_name": "David Miller",
                "borrower_type": "PERSON",
                "mobile": "0917-567-8901",
                "primary_address": "212 Birch Road, Pasig City",
            },
            {
                "borrower_id": "BRW006",
                "full_name": "Emma Wilson",
                "borrower_type": "PERSON",
                "mobile": "0917-678-9012",
                "primary_address": "333 Cedar Court, Marikina City",
            },
            {
                "borrower_id": "BRW007",
                "full_name": "Robert Taylor",
                "borrower_type": "PERSON",
                "mobile": "0917-789-0123",
                "primary_address": "444 Elm Street, Paranaque City",
            },
            {
                "borrower_id": "BRW008",
                "full_name": "Lisa Anderson",
                "borrower_type": "PERSON",
                "mobile": "0917-890-1234",
                "primary_address": "555 Spruce Avenue, Las Pinas City",
            },
            {
                "borrower_id": "BRW009",
                "full_name": "James Martin",
                "borrower_type": "PERSON",
                "mobile": "0917-901-2345",
                "primary_address": "666 Willow Lane, Muntinlupa City",
            },
            {
                "borrower_id": "BRW010",
                "full_name": "Patricia Lewis",
                "borrower_type": "PERSON",
                "mobile": "0917-012-3456",
                "primary_address": "777 Aspen Drive, Taguig City",
            },
        ]

        for borrower_data in dummy_borrowers:
            borrower, created = Borrower.objects.get_or_create(
                borrower_id=borrower_data["borrower_id"],
                defaults={**borrower_data, "created_by": user, "updated_by": user},
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created borrower {borrower_data['borrower_id']}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Borrower {borrower_data['borrower_id']} already exists"
                    )
                )

        # Load loan accounts
        self.stdout.write(self.style.SUCCESS("Loading loan accounts..."))
        dummy_accounts = [
            {
                "loan_id": "ACC001",
                "borrower_id": "BRW001",
                "loan_type": "Housing Loan",
                "booking_date": timezone.now().date() - timedelta(days=365),
                "original_principal": Decimal("2500000.00"),
                "interest_rate": Decimal("6.25"),
                "maturity_date": timezone.now().date() + timedelta(days=3650),
                "loan_security": "SECURED",
                "account_officer_id": "AO001",
                "status": "PERFORMING",
            },
            {
                "loan_id": "ACC002",
                "borrower_id": "BRW002",
                "loan_type": "Personal Loan",
                "booking_date": timezone.now().date() - timedelta(days=180),
                "original_principal": Decimal("300000.00"),
                "interest_rate": Decimal("10.50"),
                "maturity_date": timezone.now().date() + timedelta(days=1080),
                "loan_security": "UNSECURED",
                "account_officer_id": "AO002",
                "status": "PERFORMING",
            },
            {
                "loan_id": "ACC003",
                "borrower_id": "BRW003",
                "loan_type": "Auto Loan",
                "booking_date": timezone.now().date() - timedelta(days=90),
                "original_principal": Decimal("1200000.00"),
                "interest_rate": Decimal("5.75"),
                "maturity_date": timezone.now().date() + timedelta(days=1460),
                "loan_security": "SECURED",
                "account_officer_id": "AO001",
                "status": "PERFORMING",
            },
            {
                "loan_id": "ACC004",
                "borrower_id": "BRW004",
                "loan_type": "Business Loan",
                "booking_date": timezone.now().date() - timedelta(days=270),
                "original_principal": Decimal("1500000.00"),
                "interest_rate": Decimal("8.00"),
                "maturity_date": timezone.now().date() + timedelta(days=1825),
                "loan_security": "UNSECURED",
                "account_officer_id": "AO003",
                "status": "PAST_DUE",
            },
            {
                "loan_id": "ACC005",
                "borrower_id": "BRW005",
                "loan_type": "Housing Loan",
                "booking_date": timezone.now().date() - timedelta(days=450),
                "original_principal": Decimal("3500000.00"),
                "interest_rate": Decimal("7.50"),
                "maturity_date": timezone.now().date() + timedelta(days=2920),
                "loan_security": "SECURED",
                "account_officer_id": "AO002",
                "status": "PERFORMING",
            },
            {
                "loan_id": "ACC006",
                "borrower_id": "BRW006",
                "loan_type": "Education Loan",
                "booking_date": timezone.now().date() - timedelta(days=365),
                "original_principal": Decimal("500000.00"),
                "interest_rate": Decimal("4.50"),
                "maturity_date": timezone.now().date() + timedelta(days=2190),
                "loan_security": "UNSECURED",
                "account_officer_id": "AO001",
                "status": "PERFORMING",
            },
            {
                "loan_id": "ACC007",
                "borrower_id": "BRW007",
                "loan_type": "Personal Loan",
                "booking_date": timezone.now().date() - timedelta(days=200),
                "original_principal": Decimal("200000.00"),
                "interest_rate": Decimal("12.00"),
                "maturity_date": timezone.now().date() + timedelta(days=730),
                "loan_security": "UNSECURED",
                "account_officer_id": "AO003",
                "status": "NPL",
            },
            {
                "loan_id": "ACC008",
                "borrower_id": "BRW008",
                "loan_type": "Auto Loan",
                "booking_date": timezone.now().date() - timedelta(days=120),
                "original_principal": Decimal("800000.00"),
                "interest_rate": Decimal("6.50"),
                "maturity_date": timezone.now().date() + timedelta(days=1095),
                "loan_security": "SECURED",
                "account_officer_id": "AO002",
                "status": "PERFORMING",
            },
            {
                "loan_id": "ACC009",
                "borrower_id": "BRW009",
                "loan_type": "Housing Loan",
                "booking_date": timezone.now().date() - timedelta(days=300),
                "original_principal": Decimal("1800000.00"),
                "interest_rate": Decimal("5.95"),
                "maturity_date": timezone.now().date() + timedelta(days=2555),
                "loan_security": "SECURED",
                "account_officer_id": "AO001",
                "status": "PAST_DUE",
            },
            {
                "loan_id": "ACC010",
                "borrower_id": "BRW010",
                "loan_type": "Business Loan",
                "booking_date": timezone.now().date() - timedelta(days=400),
                "original_principal": Decimal("2200000.00"),
                "interest_rate": Decimal("9.25"),
                "maturity_date": timezone.now().date() + timedelta(days=1460),
                "loan_security": "UNSECURED",
                "account_officer_id": "AO003",
                "status": "CLOSED",
            },
        ]

        for data in dummy_accounts:
            borrower_id = data.pop("borrower_id")

            # Error handling for missing borrower
            try:
                borrower = Borrower.objects.get(borrower_id=borrower_id)
            except Borrower.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"  Borrower {borrower_id} not found for account {data['loan_id']}"
                    )
                )
                continue

            account, created = LoanAccount.objects.get_or_create(
                loan_id=data["loan_id"],
                defaults={
                    **data,
                    "borrower": borrower,
                    "created_by": user,
                    "updated_by": user,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  Created account {data['loan_id']}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"  Account {data['loan_id']} already exists")
                )

        self.stdout.write(
            self.style.SUCCESS(
                "\nFoundational dummy data has been loaded successfully!"
            )
        )
