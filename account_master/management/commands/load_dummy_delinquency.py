from django.core.management.base import BaseCommand
from account_master.models import Borrower, LoanAccount, DelinquencyStatus
from account_master.services.classification import (
    derive_aging_bucket,
    derive_classification,
)
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = "Loads dummy delinquency status data for existing accounts."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Loading dummy delinquency status data...")
        )

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
                self.style.ERROR("No accounts found to create delinquency status for.")
            )
            return

        for account in accounts:
            # Clear existing delinquency data for this account to avoid duplicates on re-run
            DelinquencyStatus.objects.filter(account=account).delete()

            # Create 10 dummy delinquency records for each account
            base_date = date.today() - timedelta(
                days=60
            )  # Start further back to simulate delinquency progression
            current_dpd = 0

            for i in range(10):
                as_of_date = base_date + timedelta(days=i * 5)  # Snapshots every 5 days

                # Simulate DPD progression
                current_dpd = min(
                    current_dpd + random.randint(5, 15), 400
                )  # Max DPD of 400 for simulation

                # Derive aging bucket, classification, and NPL flag via the
                # shared rule (NPL starts at 91+ DPD; buckets are range labels).
                classification = derive_classification(current_dpd)
                npl_flag = classification in ("SS", "D", "L")
                npl_date = as_of_date if npl_flag else None  # NPL date = first NPL snapshot

                # Only create record if it's actually past due for relevant classification
                if current_dpd > 0:  # Only record if there's actual delinquency
                    DelinquencyStatus.objects.create(
                        account=account,
                        as_of_date=as_of_date,
                        days_past_due=current_dpd,
                        aging_bucket=derive_aging_bucket(current_dpd),
                        classification=classification,
                        npl_flag=npl_flag,
                        npl_date=npl_date,
                    )
                    self.stdout.write(
                        f"  Created delinquency for {account.loan_id} on {as_of_date} (DPD: {current_dpd})"
                    )

        self.stdout.write(
            self.style.SUCCESS("Dummy delinquency status data loaded successfully!")
        )
