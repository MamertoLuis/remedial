import datetime
from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from account_master.models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    ECLProvisionHistory,
)


class FinancialModelsTest(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001", full_name="John Doe", primary_address="123 Main St"
        )
        self.loan = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=datetime.date(2023, 1, 1),
            maturity_date=datetime.date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            loan_type="Personal",
        )

    def test_exposure_creation_and_properties(self):
        exposure = Exposure.objects.create(
            account=self.loan,
            as_of_date=datetime.date(2023, 6, 1),
            principal_outstanding=Decimal("8000.00"),
            accrued_interest=Decimal("200.00"),
            accrued_penalty=Decimal("50.00"),
            days_past_due=15,
        )
        self.assertEqual(exposure.total_exposure, Decimal("8250.00"))

        # Test unique constraint
        with self.assertRaises(IntegrityError):
            Exposure.objects.create(
                account=self.loan,
                as_of_date=datetime.date(2023, 6, 1),
                principal_outstanding=Decimal("8000.00"),
                accrued_interest=Decimal("200.00"),
                accrued_penalty=Decimal("50.00"),
                days_past_due=15,
            )

    def test_delinquency_status_creation_and_constraints(self):
        delinquency = DelinquencyStatus.objects.create(
            account=self.loan,
            as_of_date=datetime.date(2023, 6, 1),
            days_past_due=15,
            aging_bucket="1-30",
            classification="SM",
        )
        self.assertEqual(delinquency.classification, "SM")

        # Test unique constraint
        with self.assertRaises(IntegrityError):
            DelinquencyStatus.objects.create(
                account=self.loan,
                as_of_date=datetime.date(2023, 6, 1),
                days_past_due=15,
            )

    def test_ecl_provision_history_creation_and_constraints(self):
        exposure = Exposure.objects.create(
            account=self.loan,
            as_of_date=datetime.date(2023, 6, 1),
            principal_outstanding=Decimal("8000.00"),
            accrued_interest=Decimal("200.00"),
            accrued_penalty=Decimal("50.00"),
            days_past_due=15,
        )

        ecl = ECLProvisionHistory.objects.create(
            exposure=exposure,
            as_of_date=datetime.date(2023, 6, 1),
            provision_rate=Decimal("0.0500"),
            provision_amount=Decimal("412.50"),
            is_current=True,
        )

        self.assertEqual(str(ecl), "ECL 412.50 for L001 as of 2023-06-01")

        # Test unique constraint
        with self.assertRaises(IntegrityError):
            ECLProvisionHistory.objects.create(
                exposure=exposure,
                as_of_date=datetime.date(2023, 6, 1),
                provision_rate=Decimal("0.1000"),
                provision_amount=Decimal("825.00"),
                is_current=True,
            )
