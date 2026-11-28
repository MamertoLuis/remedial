"""Tests for legacy management commands after derivation unification.

Verifies that `update_delinquency` and `load_dummy_delinquency` now derive
classification and aging buckets through the shared classification module
(loan-portfolio-metrics).
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase

from account_master.models import Borrower, LoanAccount, Exposure, DelinquencyStatus
from account_master.services.classification import (
    derive_aging_bucket,
    derive_classification,
)
from account_master.services.dashboard_service import DashboardService


class LegacyCommandsDerivationTests(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B-CMD",
            full_name="Cmd Borrower",
            borrower_type="PERSON",
        )

    def _account(self, loan_id, status):
        return LoanAccount.objects.create(
            loan_id=loan_id,
            borrower=self.borrower,
            booking_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=300),
            original_principal=Decimal("100000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="Personal",
            status=status,
        )

    def test_update_delinquency_uses_shared_derivation(self):
        account = self._account("CMD001", "PAST_DUE")
        call_command("update_delinquency", verbosity=0)
        snapshot = DelinquencyStatus.objects.get(
            account=account, as_of_date=date.today()
        )
        self.assertEqual(
            snapshot.classification, derive_classification(snapshot.days_past_due)
        )
        self.assertEqual(
            snapshot.aging_bucket, derive_aging_bucket(snapshot.days_past_due)
        )

    def test_load_dummy_uses_shared_derivation(self):
        account = self._account("CMD002", "PERFORMING")
        call_command("load_dummy_delinquency", verbosity=0)
        rows = DelinquencyStatus.objects.filter(account=account)
        self.assertTrue(rows.exists())
        for row in rows:
            self.assertEqual(
                row.classification, derive_classification(row.days_past_due)
            )
            self.assertEqual(
                row.aging_bucket, derive_aging_bucket(row.days_past_due)
            )


class RepairLegacyNplRowsTests(TestCase):
    """Tests for the legacy 90-DPD SS -> SM repair command."""

    def setUp(self):
        cache.clear()
        self.borrower = Borrower.objects.create(
            borrower_id="B-RP", full_name="Repair Borrower", borrower_type="PERSON",
        )
        today = date.today()

        # Legacy-written row: exactly 90 DPD wrongly classified SS/NPL.
        self.account = self._account("RP001", "NPL")
        self.row = DelinquencyStatus.objects.create(
            account=self.account, as_of_date=today,
            days_past_due=90, classification="SS", npl_flag=True,
            npl_date=today, snapshot_type="EVENT",
        )
        Exposure.objects.create(
            account=self.account, as_of_date=today,
            principal_outstanding=Decimal("5000.00"),
            accrued_interest=Decimal("0"), accrued_penalty=Decimal("0"),
        )

        # A correct 95-DPD NPL row that must NOT be touched.
        self.npl_account = self._account("RP002", "NPL")
        self.npl_row = DelinquencyStatus.objects.create(
            account=self.npl_account, as_of_date=today,
            days_past_due=95, classification="SS", npl_flag=True,
            npl_date=today, snapshot_type="EVENT",
        )
        Exposure.objects.create(
            account=self.npl_account, as_of_date=today,
            principal_outstanding=Decimal("7000.00"),
            accrued_interest=Decimal("0"), accrued_penalty=Decimal("0"),
        )

    def _account(self, loan_id, status):
        return LoanAccount.objects.create(
            loan_id=loan_id,
            borrower=self.borrower,
            booking_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=300),
            original_principal=Decimal("100000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="Personal",
            status=status,
        )

    def test_dry_run_reports_and_changes_nothing(self):
        call_command("repair_legacy_npl_rows", dry_run=True, verbosity=0)
        self.row.refresh_from_db()
        self.assertEqual(self.row.classification, "SS")
        self.assertTrue(self.row.npl_flag)
        self.assertIsNotNone(self.row.npl_date)

    def test_repairs_legacy_rows_and_recomputes_status(self):
        call_command("repair_legacy_npl_rows", verbosity=0)

        self.row.refresh_from_db()
        self.assertEqual(self.row.classification, "SM")
        self.assertFalse(self.row.npl_flag)
        self.assertIsNone(self.row.npl_date)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "PAST_DUE")

        # The 95-DPD NPL row is untouched.
        self.npl_row.refresh_from_db()
        self.assertEqual(self.npl_row.classification, "SS")
        self.assertTrue(self.npl_row.npl_flag)
        self.npl_account.refresh_from_db()
        self.assertEqual(self.npl_account.status, "NPL")

    def test_clears_dashboard_cache(self):
        key = DashboardService.get_cache_key("total_past_due_loans")
        DashboardService.get_total_past_due_loans()
        self.assertIsNotNone(cache.get(key))
        call_command("repair_legacy_npl_rows", verbosity=0)
        self.assertIsNone(cache.get(key))
