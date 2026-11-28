from datetime import date
from decimal import Decimal

from django.test import TestCase

from account_master.models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    ECLProvisionHistory,
)
from account_master.services.ecl_service import (
    _get_provision_rate_for_classification,
    update_ecl_provision,
    update_ecl_provision_for_account,
)


class ECLServiceTests(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            primary_address="123 Main St",
        )
        self.account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=date(2023, 1, 1),
            maturity_date=date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            loan_type="Personal",
        )
        self.as_of_date = date(2023, 6, 1)
        self.exposure = Exposure.objects.create(
            account=self.account,
            as_of_date=self.as_of_date,
            principal_outstanding=Decimal("8000.00"),
            accrued_interest=Decimal("100.00"),
            accrued_penalty=Decimal("0.00"),
            days_past_due=15,
        )
        self.delinquency = DelinquencyStatus.objects.create(
            account=self.account,
            as_of_date=self.as_of_date,
            days_past_due=15,
            classification="C",
        )

    def test_get_provision_rate_for_classification(self):
        # Stage 1
        self.assertEqual(
            _get_provision_rate_for_classification("C", 15),
            Decimal("0.01") + Decimal("0.015"),
        )
        self.assertEqual(
            _get_provision_rate_for_classification("SM", 45),
            Decimal("0.03") + Decimal("0.015"),
        )
        self.assertEqual(
            _get_provision_rate_for_classification("SM", 75),
            Decimal("0.05") + Decimal("0.015"),
        )

        # Stage 2
        self.assertEqual(
            _get_provision_rate_for_classification("SS", 45),
            Decimal("0.20") + Decimal("0.015"),
        )
        self.assertEqual(
            _get_provision_rate_for_classification("D", 75),
            Decimal("0.35") + Decimal("0.015"),
        )
        self.assertEqual(
            _get_provision_rate_for_classification("D", 100),
            Decimal("0.50") + Decimal("0.010"),
        )

        # Stage 3
        self.assertEqual(
            _get_provision_rate_for_classification("L", 120), Decimal("1.00")
        )

        # Unknown
        self.assertEqual(
            _get_provision_rate_for_classification("UNKNOWN", 15),
            Decimal("0.00") + Decimal("0.015"),
        )

    def test_update_ecl_provision(self):
        provision = update_ecl_provision(self.exposure, self.delinquency)

        self.assertEqual(provision.exposure, self.exposure)
        self.assertEqual(provision.as_of_date, self.as_of_date)
        self.assertEqual(provision.classification, "C")
        self.assertEqual(provision.days_past_due, 15)

        expected_rate = _get_provision_rate_for_classification("C", 15)
        self.assertEqual(provision.provision_rate, expected_rate)
        self.assertEqual(
            provision.provision_amount,
            self.exposure.principal_outstanding * expected_rate,
        )
        self.assertTrue(provision.is_current)

        # Test updating existing provision
        self.delinquency.classification = "SM"
        self.delinquency.days_past_due = 45
        self.delinquency.save()

        new_provision = update_ecl_provision(self.exposure, self.delinquency)

        # Old provision should be deactivated
        provision.refresh_from_db()
        self.assertFalse(provision.is_current)

        # New provision should be active
        self.assertTrue(new_provision.is_current)
        self.assertEqual(new_provision.classification, "SM")

    def test_update_ecl_provision_for_account(self):
        # Clear existing provisions created by signals
        ECLProvisionHistory.objects.all().delete()

        update_ecl_provision_for_account(self.account, self.as_of_date)

        provisions = ECLProvisionHistory.objects.filter(exposure=self.exposure)
        self.assertEqual(provisions.count(), 1)

        provision = provisions.first()
        self.assertEqual(provision.classification, "C")
        self.assertTrue(provision.is_current)

        # Test with no exposure
        no_exposure_date = date(2023, 7, 1)
        DelinquencyStatus.objects.create(
            account=self.account,
            as_of_date=no_exposure_date,
            days_past_due=30,
            classification="SM",
        )

        # Should not raise exception
        update_ecl_provision_for_account(self.account, no_exposure_date)

        # No new provision should be created for the new date
        self.assertEqual(
            ECLProvisionHistory.objects.filter(as_of_date=no_exposure_date).count(), 0
        )
