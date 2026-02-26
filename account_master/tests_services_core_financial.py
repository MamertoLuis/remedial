import datetime
import decimal
from django.test import TestCase
from account_master.models import Borrower, LoanAccount, Exposure, DelinquencyStatus
from account_master.services.core import (
    upsert_exposure,
    upsert_delinquency_status,
    _derive_aging_bucket,
    _derive_classification,
    take_snapshot,
)


class CoreFinancialServicesTests(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            borrower_type="PERSON",
            full_name="John Doe",
            primary_address="123 Main St",
            mobile="1234567890",
        )
        self.loan_account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=datetime.date(2023, 1, 1),
            maturity_date=datetime.date(2024, 1, 1),
            original_principal=decimal.Decimal("10000.00"),
            interest_rate=decimal.Decimal("5.00"),
            loan_type="PERSONAL",
            status="PERFORMING",
        )
        self.as_of_date = datetime.date(2023, 6, 1)

    def test_upsert_exposure_creates_delinquency_status(self):
        exposure_data = {
            "principal_outstanding": decimal.Decimal("5000.00"),
            "accrued_interest": decimal.Decimal("100.00"),
            "accrued_penalty": decimal.Decimal("0.00"),
            "days_past_due": 45,
        }
        exposure, created = upsert_exposure(
            account=self.loan_account,
            as_of_date=self.as_of_date,
            defaults=exposure_data,
        )
        self.assertTrue(created)
        self.assertEqual(exposure.principal_outstanding, decimal.Decimal("5000.00"))

        # Verify delinquency status was auto-created
        delinquency = DelinquencyStatus.objects.get(
            account=self.loan_account, as_of_date=self.as_of_date
        )
        self.assertEqual(delinquency.days_past_due, 45)
        self.assertEqual(delinquency.aging_bucket, "31-60")
        self.assertEqual(delinquency.classification, "SM")

    def test_upsert_delinquency_status_derives_bucket_and_updates_loan(self):
        delinquency_data = {
            "days_past_due": 100,
            # aging_bucket omitted to test derivation
        }
        delinquency, created = upsert_delinquency_status(
            account=self.loan_account,
            as_of_date=self.as_of_date,
            defaults=delinquency_data,
        )
        self.assertTrue(created)
        self.assertEqual(delinquency.aging_bucket, "91-120")
        self.assertEqual(
            delinquency.classification, "C"
        )  # Default is C if not provided in defaults

        # Let's provide classification to see loan status update
        delinquency_data_2 = {"days_past_due": 100, "classification": "SS"}
        delinquency2, created2 = upsert_delinquency_status(
            account=self.loan_account,
            as_of_date=self.as_of_date,
            defaults=delinquency_data_2,
        )
        self.assertFalse(created2)

        self.loan_account.refresh_from_db()
        self.assertEqual(self.loan_account.status, "NPL")

    def test_derive_aging_bucket(self):
        self.assertEqual(_derive_aging_bucket(0), "Current")
        self.assertEqual(_derive_aging_bucket(1), "1-30")
        self.assertEqual(_derive_aging_bucket(30), "1-30")
        self.assertEqual(_derive_aging_bucket(31), "31-60")
        self.assertEqual(_derive_aging_bucket(60), "31-60")
        self.assertEqual(_derive_aging_bucket(61), "61-90")
        self.assertEqual(_derive_aging_bucket(90), "61-90")
        self.assertEqual(_derive_aging_bucket(91), "91-120")
        self.assertEqual(_derive_aging_bucket(120), "91-120")
        self.assertEqual(_derive_aging_bucket(121), "121-180")
        self.assertEqual(_derive_aging_bucket(180), "121-180")
        self.assertEqual(_derive_aging_bucket(181), "181-360")
        self.assertEqual(_derive_aging_bucket(360), "181-360")
        self.assertEqual(_derive_aging_bucket(361), "Over 360")

    def test_derive_classification(self):
        self.assertEqual(_derive_classification(0), "C")
        self.assertEqual(_derive_classification(1), "SM")
        self.assertEqual(_derive_classification(90), "SM")
        self.assertEqual(_derive_classification(91), "SS")
        self.assertEqual(_derive_classification(180), "SS")
        self.assertEqual(_derive_classification(181), "D")
        self.assertEqual(_derive_classification(360), "D")
        self.assertEqual(_derive_classification(361), "L")

    def test_take_snapshot(self):
        exposure_data = {
            "principal_outstanding": decimal.Decimal("8000.00"),
            "accrued_interest": decimal.Decimal("200.00"),
            "days_past_due": 150,
        }
        delinquency_data = {
            "days_past_due": 150,
            "classification": "SS",
        }

        take_snapshot(
            account=self.loan_account,
            as_of_date=self.as_of_date,
            exposure_data=exposure_data,
            delinquency_data=delinquency_data,
        )

        # Verify both were created
        exposure = Exposure.objects.get(
            account=self.loan_account, as_of_date=self.as_of_date
        )
        self.assertEqual(exposure.principal_outstanding, decimal.Decimal("8000.00"))

        delinquency = DelinquencyStatus.objects.get(
            account=self.loan_account, as_of_date=self.as_of_date
        )
        self.assertEqual(delinquency.classification, "SS")
        self.assertEqual(delinquency.aging_bucket, "121-180")

        # Verify loan status updated
        self.loan_account.refresh_from_db()
        self.assertEqual(self.loan_account.status, "NPL")
