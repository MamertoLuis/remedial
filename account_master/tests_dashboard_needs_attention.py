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


class PortfolioMetricsTests(TestCase):
    """Dashboard portfolio metrics under the umbrella past-due definition."""

    def setUp(self):
        cache.clear()
        self.user = self._make_user()
        self.borrower = Borrower.objects.create(
            borrower_id="B-PM", full_name="PM", borrower_type="PERSON",
        )

    @staticmethod
    def _make_user():
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            username="portmetrics", email="pm@example.com", password="pw"
        )

    def _account(self, loan_id, status, balance):
        account = LoanAccount.objects.create(
            loan_id=loan_id,
            borrower=self.borrower,
            booking_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=300),
            original_principal=Decimal("100000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="Personal",
            status=status,
        )
        Exposure.objects.create(
            account=account, as_of_date=date.today(),
            principal_outstanding=Decimal(str(balance)),
            accrued_interest=Decimal("100.00"), accrued_penalty=Decimal("0"),
        )
        return account

    def test_total_past_due_includes_npl(self):
        self._account("PM001", "PAST_DUE", 40000)
        self._account("PM002", "NPL", 60000)
        self._account("PM003", "PERFORMING", 50000)

        self.assertEqual(
            DashboardService.get_total_past_due_loans(), Decimal("100000.00")
        )

    def test_past_due_ratio_mixed_portfolio(self):
        # Numerator: PAST_DUE + NPL = 2. Denominator: active portfolio
        # (excludes CLOSED and WRITEOFF) = 3 -> 66.67%.
        self._account("PM010", "PAST_DUE", 100)
        self._account("PM011", "NPL", 100)
        self._account("PM012", "PERFORMING", 100)
        self._account("PM013", "WRITEOFF", 100)
        self._account("PM014", "CLOSED", 0)

        self.assertEqual(DashboardService.get_past_due_ratio(), 66.67)

    def test_past_due_ratio_extremes(self):
        self._account("PM020", "PAST_DUE", 100)
        self._account("PM021", "NPL", 100)
        self.assertEqual(DashboardService.get_past_due_ratio(), 100.0)

        cache.clear()
        self.assertEqual(DashboardService.get_past_due_ratio(), 100.0)

    def test_past_due_ratio_zero_when_none(self):
        self._account("PM030", "PERFORMING", 100)
        self.assertEqual(DashboardService.get_past_due_ratio(), 0.0)

    def test_npl_ratio_excludes_writeoff(self):
        # NPL 1 account, active portfolio (excl. CLOSED/WRITEOFF) = 1 -> 100%.
        self._account("PM040", "NPL", 100)
        self._account("PM041", "WRITEOFF", 100)
        self._account("PM042", "CLOSED", 0)

        self.assertEqual(DashboardService.get_npl_ratio(), 100.0)

    def test_portfolio_by_status_umbrella_nested(self):
        self._account("PM050", "PERFORMING", 10000)
        self._account("PM051", "PAST_DUE", 20000)
        self._account("PM052", "NPL", 30000)
        self._account("PM053", "WRITEOFF", 40000)

        items = DashboardService.get_portfolio_by_status()
        self.assertEqual([i["name"] for i in items], ["Current", "Past Due", "Written Off"])

        current = items[0]
        past_due = items[1]
        written_off = items[2]

        self.assertEqual(current["balance"], Decimal("10000.00"))
        self.assertEqual(current["percentage"], 10.0)
        # Umbrella: Past Due includes the NPL balance, NPL exposed as subset.
        self.assertEqual(past_due["balance"], Decimal("50000.00"))
        self.assertEqual(past_due["percentage"], 50.0)
        self.assertEqual(past_due["npl"]["balance"], Decimal("30000.00"))
        self.assertEqual(past_due["npl"]["percentage"], 30.0)
        self.assertEqual(written_off["balance"], Decimal("40000.00"))
        self.assertEqual(written_off["percentage"], 40.0)

        # Slices sum to the full portfolio.
        total = sum(i["balance"] for i in items)
        self.assertEqual(total, Decimal("100000.00"))

    def test_dashboard_renders_past_due_ratio_tile(self):
        from django.test import Client
        from django.urls import reverse

        self._account("PM060", "PAST_DUE", 100)
        self._account("PM061", "NPL", 100)
        self._account("PM062", "PERFORMING", 100)

        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Past Due Ratio")
        self.assertContains(response, "66.67%")
