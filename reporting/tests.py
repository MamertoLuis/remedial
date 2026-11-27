"""Reporting tests for the umbrella past-due definition (loan-portfolio-metrics)."""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from account_master.models import Borrower, LoanAccount, Exposure, DelinquencyStatus


class _ReportFixtures(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B-RPT", full_name="Report Borrower", borrower_type="PERSON",
        )

    def _account(self, loan_id, status, officer="AO1"):
        return LoanAccount.objects.create(
            loan_id=loan_id,
            borrower=self.borrower,
            booking_date=date(2023, 1, 1),
            maturity_date=date(2025, 1, 1),
            original_principal=Decimal("100000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="Personal",
            account_officer_id=officer,
            status=status,
        )

    def _snapshot(self, account, dpd, bucket, classification, npl_flag, principal):
        Exposure.objects.create(
            account=account, as_of_date=date(2024, 6, 1),
            principal_outstanding=Decimal(str(principal)),
            accrued_interest=Decimal("0"), accrued_penalty=Decimal("0"),
        )
        DelinquencyStatus.objects.create(
            account=account, as_of_date=date(2024, 6, 1),
            days_past_due=dpd, aging_bucket=bucket,
            classification=classification, npl_flag=npl_flag,
        )


class PastDueAgingSummaryTests(_ReportFixtures):
    def test_npl_account_populates_high_buckets(self):
        # A 45-DPD PAST_DUE account and a 95-DPD NPL account for the same
        # officer: the 91-120 bucket must now include the NPL account.
        past_due = self._account("AG001", "PAST_DUE")
        npl = self._account("AG002", "NPL")
        self._snapshot(past_due, 45, "31-60", "SM", False, 30000)
        self._snapshot(npl, 95, "91-120", "SS", True, 50000)

        response = self.client.get(reverse("reporting:past_due_aging_summary"))
        self.assertEqual(response.status_code, 200)
        report_data = response.context["report_data"]
        self.assertEqual(len(report_data), 1)
        officer = report_data[0]
        self.assertEqual(officer["buckets"]["31-60"]["amount"], Decimal("30000.00"))
        self.assertEqual(officer["buckets"]["91-120"]["amount"], Decimal("50000.00"))
        self.assertEqual(officer["buckets"]["91-120"]["accounts"], 1)
        self.assertEqual(officer["officer_total_amount"], Decimal("80000.00"))


class LoanOfficerPerformanceSummaryTests(_ReportFixtures):
    def test_past_due_balance_is_umbrella(self):
        pf1 = self._account("PF001", "PAST_DUE")
        pf2 = self._account("PF002", "NPL")
        pf3 = self._account("PF003", "PERFORMING")
        for acc, principal in ((pf1, 20000), (pf2, 30000), (pf3, 10000)):
            self._snapshot(acc, 60, "31-60", "SM", False, principal)

        response = self.client.get(
            reverse("reporting:loan_officer_performance_summary")
        )
        self.assertEqual(response.status_code, 200)
        officer = next(
            d for d in response.context["report_data"] if d["officer"] == "AO1"
        )
        # Umbrella past due = PAST_DUE + NPL balances; NPL portion still reported.
        self.assertEqual(officer["past_due_balance"], Decimal("50000.00"))
        self.assertEqual(officer["npl_balance"], Decimal("30000.00"))
        self.assertEqual(officer["portfolio_balance"], Decimal("60000.00"))
