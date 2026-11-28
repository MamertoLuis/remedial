from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from account_master.models import Borrower, LoanAccount, Exposure, ECLProvisionHistory
from account_master.services.provision_service import (
    compute_provision_amount,
    create_provision_entry,
)


class ProvisionServiceTests(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            borrower_type="PERSON",
            full_name="John Doe",
            primary_address="123 Main St",
        )
        self.loan_account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=timezone.now().date(),
            maturity_date=timezone.now().date(),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            loan_type="PERSONAL",
            status="PERFORMING",
        )
        self.exposure = Exposure.objects.create(
            account=self.loan_account,
            as_of_date=timezone.now().date(),
            principal_outstanding=Decimal("5000.00"),
            accrued_interest=Decimal("100.00"),
            accrued_penalty=Decimal("50.00"),
            days_past_due=10,
        )
        # Total exposure = 5000 + 100 + 50 = 5150.00

    def test_compute_provision_amount_normal(self):
        amount = compute_provision_amount(Decimal("5150.00"), Decimal("0.10"))
        self.assertEqual(amount, Decimal("515.00"))

    def test_compute_provision_amount_rounding(self):
        # 5150.00 * 0.105 = 540.75
        amount = compute_provision_amount(Decimal("5150.00"), Decimal("0.105"))
        self.assertEqual(amount, Decimal("540.75"))

        # 5150.00 * 0.1055 = 543.325 -> 543.33
        amount = compute_provision_amount(Decimal("5150.00"), Decimal("0.1055"))
        self.assertEqual(amount, Decimal("543.33"))

    def test_compute_provision_amount_none_values(self):
        amount = compute_provision_amount(None, Decimal("0.10"))
        self.assertEqual(amount, Decimal("0.00"))

        amount = compute_provision_amount(Decimal("5150.00"), None)
        self.assertEqual(amount, Decimal("0.00"))

        amount = compute_provision_amount(None, None)
        self.assertEqual(amount, Decimal("0.00"))

    def test_create_provision_entry_success(self):
        entry = create_provision_entry(
            exposure=self.exposure,
            provision_rate=Decimal("0.10"),
            method="RULE_BASED",
            remarks="Test provision",
            classification="SM",
            days_past_due=10,
        )

        self.assertIsInstance(entry, ECLProvisionHistory)
        self.assertEqual(entry.exposure, self.exposure)
        self.assertEqual(entry.provision_rate, Decimal("0.10"))
        self.assertEqual(entry.provision_amount, Decimal("515.00"))
        self.assertEqual(entry.method, "RULE_BASED")
        self.assertEqual(entry.remarks, "Test provision")
        self.assertEqual(entry.classification, "SM")
        self.assertEqual(entry.days_past_due, 10)
        self.assertTrue(entry.is_current)

    def test_create_provision_entry_deactivates_old(self):
        # Create first entry
        entry1 = create_provision_entry(
            exposure=self.exposure,
            provision_rate=Decimal("0.10"),
        )
        self.assertTrue(entry1.is_current)

        # Create second entry
        entry2 = create_provision_entry(
            exposure=self.exposure,
            provision_rate=Decimal("0.20"),
        )

        # Refresh entry1 from db
        entry1.refresh_from_db()

        self.assertFalse(entry1.is_current)
        self.assertTrue(entry2.is_current)
        self.assertEqual(entry2.provision_amount, Decimal("1030.00"))

    def test_create_provision_entry_none_rate(self):
        with self.assertRaisesMessage(ValueError, "Provision rate is required."):
            create_provision_entry(
                exposure=self.exposure,
                provision_rate=None,
            )

    def test_create_provision_entry_negative_rate(self):
        with self.assertRaisesMessage(ValueError, "Provision rate cannot be negative."):
            create_provision_entry(
                exposure=self.exposure,
                provision_rate=Decimal("-0.10"),
            )
