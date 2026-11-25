"""Tests for the dashboard needs-attention triage feed (ui-workspace)."""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.core.cache import cache

from account_master.models import Borrower, LoanAccount, Exposure, DelinquencyStatus
from account_master.services.dashboard_service import DashboardService


class NeedsAttentionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = self._make_user()

    @staticmethod
    def _make_user():
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            username="needsatt", email="n@example.com", password="pw"
        )

    def _account(self, loan_id, status, borrower):
        return LoanAccount.objects.create(
            loan_id=loan_id,
            borrower=borrower,
            booking_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=300),
            original_principal=Decimal("100000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="Personal",
            status=status,
        )

    def test_orders_by_days_past_due_descending_and_limits(self):
        borrower = Borrower.objects.create(
            borrower_id="B-NA", full_name="Needs Attention",
            borrower_type="PERSON",
        )
        a1 = self._account("NA001", "PAST_DUE", borrower)
        a2 = self._account("NA002", "NPL", borrower)
        a3 = self._account("NA003", "PAST_DUE", borrower)
        for account, dpd in ((a1, 15), (a2, 90), (a3, 45)):
            Exposure.objects.create(
                account=account, as_of_date=date.today(),
                principal_outstanding=Decimal("50000.00"),
                accrued_interest=Decimal("100.00"), accrued_penalty=Decimal("0"),
                created_by=self.user,
            )
            DelinquencyStatus.objects.create(
                account=account, as_of_date=date.today(),
                days_past_due=dpd, snapshot_type="EVENT",
            )
        # A performing account with no delinquency must not appear.
        self._account("NA004", "PERFORMING", borrower)

        rows = DashboardService.get_needs_attention(limit=2)
        self.assertEqual([r.loan_id for r in rows], ["NA002", "NA003"])
        self.assertEqual(rows[0].days_past_due, 90)
        self.assertEqual(rows[1].days_past_due, 45)

    def test_annotated_fields_present(self):
        borrower = Borrower.objects.create(
            borrower_id="B-NB", full_name="B", borrower_type="PERSON",
        )
        account = self._account("NB001", "NPL", borrower)
        Exposure.objects.create(
            account=account, as_of_date=date.today(),
            principal_outstanding=Decimal("25000.00"),
            accrued_interest=Decimal("0"), accrued_penalty=Decimal("0"),
            created_by=self.user,
        )
        DelinquencyStatus.objects.create(
            account=account, as_of_date=date.today(),
            days_past_due=30, snapshot_type="EVENT",
        )

        rows = DashboardService.get_needs_attention()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.outstanding_balance, Decimal("25000.00"))
        self.assertEqual(row.days_past_due, 30)
        self.assertIsNotNone(row.borrower)
        self.assertEqual(row.borrower_id, borrower.borrower_id)

    def test_empty_when_no_attention_accounts(self):
        self.assertEqual(DashboardService.get_needs_attention(), [])
