from django.core.management.base import BaseCommand
from account_master.models import Borrower, LoanAccount, Exposure
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = "Loads dummy exposure data for existing accounts."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Loading dummy exposure data..."))

        # Ensure there are some borrowers and accounts
        if not Borrower.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No borrowers found. Creating dummy borrowers and accounts."
                )
            )
            for i in range(1, 3):
                borrower, created = Borrower.objects.get_or_create(
                    borrower_id=f"B{i:04d}",
                    defaults={
                        "full_name": f"Borrower {i} Test",
                        "borrower_type": "PERSON",
                        "mobile": f"555-000-{i:03d}",
                        "primary_address": f"123 Main St, City {i}",
                    },
                )
                if created:
                    self.stdout.write(f"Created borrower: {borrower.borrower_id}")

                account, created = LoanAccount.objects.get_or_create(
                    loan_id=f"ACC{i:04d}",
                    defaults={
                        "borrower": borrower,
                        "loan_type": "Consumer",
                        "booking_date": date(2023, 1, 1),
                        "original_principal": 100000.00 * i,
                        "interest_rate": 0.05,
                        "maturity_date": date(2025, 1, 1),
                        "account_officer_id": "AO001",
                        "status": "PERFORMING",
                    },
                )
                if created:
                    self.stdout.write(f"Created account: {account.loan_id}")

        accounts = LoanAccount.objects.all()

        if not accounts.exists():
            self.stdout.write(
                self.style.ERROR("No accounts found to create exposure for.")
            )
            return

        for account in accounts:
            # Clear existing exposure data for this account to avoid duplicates on re-run
            Exposure.objects.filter(account=account).delete()

            # Create 10 dummy exposure records for each account
            base_date = date.today() - timedelta(days=30)
            for i in range(10):
                as_of_date = base_date + timedelta(days=i * 3)
                principal = float(account.original_principal) * (0.95 - (i * 0.01))
                interest = principal * 0.01 * (i + 1)
                penalty = principal * 0.005 * i
                total_exposure = principal + interest + penalty

                Exposure.objects.create(
                    account=account,
                    as_of_date=as_of_date,
                    principal_outstanding=round(principal, 2),
                    accrued_interest=round(interest, 2),
                    accrued_penalty=round(penalty, 2),
                    total_exposure=round(total_exposure, 2),
                )
                self.stdout.write(
                    f"  Created exposure for {account.loan_id} on {as_of_date}"
                )

        self.stdout.write(
            self.style.SUCCESS("Dummy exposure data loaded successfully!")
        )
