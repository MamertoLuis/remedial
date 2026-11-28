"""Tests for the demo database seeder (specs/demo-data/spec.md).

Runs on the isolated test database; seeding is exercised via the
``seed_demo`` command and the ``account_master.services.demo_seed`` layer.
"""

from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from account_master.models import (
    Borrower,
    DelinquencyStatus,
    ECLProvisionHistory,
    EscalationState,
    Exposure,
    LitigationEntry,
    LoanAccount,
)
from account_master.services import demo_seed
from account_master.services.litigation_service import has_approved_litigation_entry


def _run_seed(seed=None):
    if seed is None:
        call_command("seed_demo", verbosity=0)
    else:
        call_command("seed_demo", seed=seed, verbosity=0)


class DemoSeedGuardTests(TestCase):
    def test_refuses_on_organic_rows_and_writes_nothing(self):
        borrower = Borrower.objects.create(
            borrower_id="ORG001", full_name="Organic", borrower_type="PERSON",
            primary_address="",
        )
        account = LoanAccount.objects.create(
            loan_id="99-99-99-9999-9999",
            borrower=borrower,
            booking_date=date(2024, 1, 1),
            maturity_date=date(2025, 1, 1),
            original_principal=Decimal("10000"),
            interest_rate=Decimal("0.05"),
            loan_type="TERM",
            account_officer_id="AO",
            status="PERFORMING",
        )
        Exposure.objects.create(
            account=account,
            as_of_date=date(2024, 6, 1),
            principal_outstanding=Decimal("8000"),
            accrued_interest=Decimal("0"),
            accrued_penalty=Decimal("0"),
            source="IACCS",
        )

        with self.assertRaises(CommandError) as cm:
            _run_seed()
        self.assertIn("refuses to run", str(cm.exception))

        # Guard runs before any write: no demo users, no demo accounts.
        from django.contrib.auth import get_user_model

        self.assertFalse(get_user_model().objects.filter(username="demo-officer").exists())
        self.assertFalse(LoanAccount.objects.filter(loan_id__in=demo_seed.DEMO_ACCOUNT_IDS).exists())

    def test_guard_passes_on_empty_database(self):
        # Fresh database: seeding proceeds and creates demo accounts.
        _run_seed()
        self.assertEqual(
            LoanAccount.objects.filter(loan_id__in=demo_seed.DEMO_ACCOUNT_IDS).count(),
            10,
        )


class DemoSeedCascadeTests(TestCase):
    def setUp(self):
        _run_seed(seed=42)

    def test_demo_users_have_roles_and_staff_invariant(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        for username, role in demo_seed.DEMO_USERS.items():
            user = User.objects.get(username=username)
            self.assertEqual(user.role, role)
            self.assertEqual(user.is_staff, role == "SYSTEM_ADMINISTRATOR")

    def test_portfolio_and_snapshots_are_bounded(self):
        accounts = LoanAccount.objects.filter(loan_id__in=demo_seed.DEMO_ACCOUNT_IDS)
        self.assertEqual(accounts.count(), 10)
        for account in accounts:
            self.assertEqual(
                Exposure.objects.filter(account=account).count(), demo_seed.WEEKS
            )

    def test_npl_account_derived_through_cascade(self):
        # ACC002 is the 'deteriorating' arc -> crosses 90 DPD -> NPL.
        account = LoanAccount.objects.get(loan_id="ACC002")
        self.assertEqual(account.status, "NPL")
        latest = (
            DelinquencyStatus.objects.filter(account=account)
            .order_by("-as_of_date")
            .first()
        )
        self.assertIn(latest.classification, ("SS", "D", "L"))
        self.assertTrue(latest.npl_flag)
        # ECL was produced by the delinquency post-save cascade.
        self.assertTrue(ECLProvisionHistory.objects.filter(exposure__account=account).exists())
        # The escalation ladder opened when the account turned delinquent.
        open_state = EscalationState.objects.filter(
            account=account, status__in=("PENDING", "ACTIVE", "PAUSED")
        ).exists()
        self.assertTrue(open_state)

    def test_cured_account_closes_ladder_with_cure_reason(self):
        # ACC003 is the 'cured' arc -> ends performing with a CURED closure.
        account = LoanAccount.objects.get(loan_id="ACC003")
        self.assertEqual(account.status, "PERFORMING")
        state = EscalationState.objects.filter(account=account).order_by("-updated_at").first()
        self.assertEqual(state.status, EscalationState.Status.CLOSED)
        self.assertEqual(state.closed_reason, EscalationState.CloseReason.CURED)

    def test_written_off_sentinel_account(self):
        # ACC005 is the 'written-off' arc -> final principal 1.00 sentinel.
        account = LoanAccount.objects.get(loan_id="ACC005")
        self.assertEqual(account.status, "WRITEOFF")
        final = Exposure.objects.filter(account=account).order_by("-as_of_date").first()
        self.assertEqual(final.principal_outstanding, Decimal("1.00"))

    def test_litigation_account_has_approved_entry(self):
        # ACC006 is the 'litigation' arc -> approved entry satisfies the gate.
        account = LoanAccount.objects.get(loan_id="ACC006")
        entry = LitigationEntry.objects.get(account=account)
        self.assertEqual(entry.status, LitigationEntry.Status.APPROVED)
        self.assertTrue(has_approved_litigation_entry(account))


class DemoSeedDeterminismTests(TestCase):
    def _snapshots(self, loan_id):
        account = LoanAccount.objects.get(loan_id=loan_id)
        return [
            (e.as_of_date, e.principal_outstanding, e.days_past_due)
            for e in Exposure.objects.filter(account=account).order_by("as_of_date")
        ]

    def test_rerun_is_idempotent(self):
        _run_seed(seed=7)
        baseline_accounts = LoanAccount.objects.filter(
            loan_id__in=demo_seed.DEMO_ACCOUNT_IDS
        ).count()
        baseline_exposures = Exposure.objects.filter(
            account__loan_id__in=demo_seed.DEMO_ACCOUNT_IDS
        ).count()

        _run_seed(seed=7)
        self.assertEqual(
            LoanAccount.objects.filter(loan_id__in=demo_seed.DEMO_ACCOUNT_IDS).count(),
            baseline_accounts,
        )
        self.assertEqual(
            Exposure.objects.filter(account__loan_id__in=demo_seed.DEMO_ACCOUNT_IDS).count(),
            baseline_exposures,
        )

    def test_same_seed_reproduces_snapshot_values(self):
        _run_seed(seed=7)
        first = self._snapshots("ACC002")
        _run_seed(seed=7)
        second = self._snapshots("ACC002")
        self.assertEqual(first, second)

    def test_different_seed_changes_generated_values(self):
        _run_seed(seed=7)
        first = self._snapshots("ACC002")
        _run_seed(seed=8)
        second = self._snapshots("ACC002")
        self.assertNotEqual(first, second)