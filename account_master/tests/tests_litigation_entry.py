"""Tests for the account-level litigation entry (change account-level-litigation-entry).

Covers: raise (officer-only, one-active rule, validation), approve/reject
(manager-only, re-raise after rejection), and the approved-entry helper that
feeds the strategy entry gate.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from account_master.models import Borrower, LitigationEntry, LoanAccount
from account_master.services.litigation_service import (
    LitigationEntryError,
    approve_litigation_entry,
    get_active_entry,
    has_approved_litigation_entry,
    raise_litigation_entry,
    reject_litigation_entry,
)

User = get_user_model()


def _today():
    return timezone.now().date()


def _user(role, username):
    return User.objects.create_user(username=username, password="pw", role=role)


def _borrower(borrower_id="B-LIT-001"):
    return Borrower.objects.create(
        borrower_id=borrower_id,
        borrower_type="PERSON",
        full_name="Litigation Borrower",
        primary_address="1 Court Rd",
    )


def _account(loan_id="L-LIT-001", **overrides):
    defaults = {
        "loan_id": loan_id,
        "borrower": _borrower(borrower_id=f"B-{loan_id}"),
        "booking_date": datetime.date(2023, 1, 1),
        "maturity_date": datetime.date(2026, 1, 1),
        "original_principal": Decimal("10000.00"),
        "interest_rate": Decimal("12.00"),
        "loan_type": "Personal",
        "loan_security": "SECURED",
        "status": "NPL",
    }
    defaults.update(overrides)
    return LoanAccount.objects.create(**defaults)


class LitigationEntryServiceTests(TestCase):
    """Tasks 2.1 - 2.2: raise, one-active rule and manager approve/reject."""

    def setUp(self):
        self.account = _account()
        self.officer = _user(User.Role.ACCOUNT_OFFICER, "officer")
        self.manager = _user(User.Role.MANAGER, "manager")
        self.other = _user(User.Role.BOARD_MEMBER, "board")

    def test_officer_raises_pending_entry(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Account already in litigation.",
            officer=self.officer,
        )
        self.assertEqual(entry.status, LitigationEntry.Status.PENDING_APPROVAL)
        self.assertEqual(entry.raised_by, self.officer)
        self.assertEqual(entry.account, self.account)
        self.assertEqual(entry.rationale, "Account already in litigation.")

    def test_only_officer_can_raise(self):
        with self.assertRaises(LitigationEntryError):
            raise_litigation_entry(
                account=self.account,
                strategy_type="Legal Action",
                start_date=_today(),
                rationale="Should be declined.",
                officer=self.manager,
            )

    def test_one_active_entry_per_account(self):
        raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="First entry.",
            officer=self.officer,
        )
        with self.assertRaises(LitigationEntryError):
            raise_litigation_entry(
                account=self.account,
                strategy_type="Foreclosure",
                start_date=_today(),
                rationale="Second entry.",
                officer=self.officer,
            )

    def test_partial_unique_constraint_enforces_one_active(self):
        raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="First entry.",
            officer=self.officer,
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                LitigationEntry.objects.create(
                    account=self.account,
                    strategy_type="Foreclosure",
                    start_date=_today(),
                    status=LitigationEntry.Status.PENDING_APPROVAL,
                )

    def test_manager_approves_entry(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Already in litigation.",
            officer=self.officer,
        )
        approved = approve_litigation_entry(
            entry, approver=self.manager, notes="Granted."
        )
        self.assertEqual(approved.status, LitigationEntry.Status.APPROVED)
        self.assertEqual(approved.decided_by, self.manager)
        self.assertTrue(has_approved_litigation_entry(self.account))

    def test_manager_reject_allows_rerraise(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Already in litigation.",
            officer=self.officer,
        )
        rejected = reject_litigation_entry(
            entry, approver=self.manager, notes="Insufficient evidence."
        )
        self.assertEqual(rejected.status, LitigationEntry.Status.REJECTED)
        self.assertFalse(has_approved_litigation_entry(self.account))
        # A rejected entry is no longer active, so a re-raise is permitted.
        second = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Re-raised after rejection.",
            officer=self.officer,
        )
        self.assertEqual(second.status, LitigationEntry.Status.PENDING_APPROVAL)
        self.assertEqual(get_active_entry(self.account), second)

    def test_non_manager_cannot_decide(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Already in litigation.",
            officer=self.officer,
        )
        with self.assertRaises(LitigationEntryError):
            approve_litigation_entry(entry, approver=self.other, notes="no")
        with self.assertRaises(LitigationEntryError):
            reject_litigation_entry(entry, approver=self.officer, notes="no")
        self.assertEqual(entry.status, LitigationEntry.Status.PENDING_APPROVAL)

    def test_invalid_strategy_type_rejected(self):
        with self.assertRaises(LitigationEntryError):
            raise_litigation_entry(
                account=self.account,
                strategy_type="Write-Off",
                start_date=_today(),
                rationale="Not litigation.",
                officer=self.officer,
            )


class LitigationEntryViewTests(TestCase):
    """Tasks 4.x - 5.x: officer raise flow and manager decision flow."""

    def setUp(self):
        self.client = Client()
        self.account = _account()
        self.officer = _user(User.Role.ACCOUNT_OFFICER, "vofficer")
        self.manager = _user(User.Role.MANAGER, "vmanager")
        self.board = _user(User.Role.BOARD_MEMBER, "vboard")
        self.raise_url = reverse("raise_litigation_entry", args=[self.account.loan_id])

    def _raise_data(self, **overrides):
        data = {
            "strategy_type": "Legal Action",
            "start_date": str(_today()),
            "rationale": "Account already in legal proceedings.",
        }
        data.update(overrides)
        return data

    def test_ladder_page_links_to_raise(self):
        self.client.force_login(self.officer)
        response = self.client.get(
            reverse("escalation_ladder_detail", args=[self.account.loan_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse("raise_litigation_entry", args=[self.account.loan_id]), response.content.decode())

    def test_officer_raise_creates_pending_entry_and_redirects(self):
        self.client.force_login(self.officer)
        response = self.client.post(self.raise_url, self._raise_data())
        self.assertRedirects(
            response, reverse("escalation_ladder_detail", args=[self.account.loan_id])
        )
        entry = self.account.litigation_entries.get()
        self.assertEqual(entry.status, LitigationEntry.Status.PENDING_APPROVAL)
        self.assertEqual(entry.raised_by, self.officer)

    def test_non_officer_cannot_raise(self):
        for user in (self.manager, self.board):
            self.client.force_login(user)
            response = self.client.post(self.raise_url, self._raise_data())
            self.assertEqual(response.status_code, 403)
        self.assertFalse(self.account.litigation_entries.exists())

    def test_manager_queue_lists_pending(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Already in litigation.",
            officer=self.officer,
        )
        self.client.force_login(self.manager)
        response = self.client.get(reverse("litigation_entry_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(entry.litigation_id), response.content.decode())

    def test_manager_decision_transitions_status(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Foreclosure",
            start_date=_today(),
            rationale="Collateral recovery needed.",
            officer=self.officer,
        )
        self.client.force_login(self.manager)
        self.client.post(
            reverse("decide_litigation_entry", args=[entry.litigation_id]),
            {"decision": "APPROVE", "decision_notes": "Approved."},
        )
        entry.refresh_from_db()
        self.assertEqual(entry.status, LitigationEntry.Status.APPROVED)
        self.assertEqual(entry.decided_by, self.manager)

    def test_manager_reject_transitions_status(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Already in litigation.",
            officer=self.officer,
        )
        self.client.force_login(self.manager)
        self.client.post(
            reverse("decide_litigation_entry", args=[entry.litigation_id]),
            {"decision": "REJECT", "decision_notes": "No evidence."},
        )
        entry.refresh_from_db()
        self.assertEqual(entry.status, LitigationEntry.Status.REJECTED)

    def test_non_manager_cannot_decide(self):
        entry = raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Already in litigation.",
            officer=self.officer,
        )
        self.client.force_login(self.officer)
        response = self.client.get(
            reverse("decide_litigation_entry", args=[entry.litigation_id])
        )
        self.assertEqual(response.status_code, 403)

class ApprovalQueueHubTests(TestCase):
    """Task 4.1: the manager approval queue surfaces litigation entries."""

    def setUp(self):
        self.client = Client()
        self.account = _account(loan_id="L-HUB-001")
        self.officer = _user(User.Role.ACCOUNT_OFFICER, "hub-officer")
        self.manager = _user(User.Role.MANAGER, "hub-manager")
        self.approval_url = reverse("approval_queue")

    def _raise_entry(self, strategy_type="Legal Action"):
        return raise_litigation_entry(
            account=self.account,
            strategy_type=strategy_type,
            start_date=_today(),
            rationale="Account already in litigation.",
            officer=self.officer,
        )

    def test_default_tab_is_strategy(self):
        entry = self._raise_entry()
        self.client.force_login(self.manager)
        response = self.client.get(self.approval_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Strategy Approvals", body)
        # Default tab shows the strategy view, not the litigation panel.
        self.assertIn("Queue is empty", body)
        self.assertNotIn(entry.account.loan_id, body)
        self.assertNotIn("Litigation Entries</h1>", body)

    def test_litigation_tab_renders_pending_entry(self):
        entry = self._raise_entry()
        self.client.force_login(self.manager)
        response = self.client.get(self.approval_url, {"tab": "litigation"})
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Litigation Entries", body)
        self.assertIn(entry.account.loan_id, body)
        self.assertIn(entry.strategy_type, body)

    def test_inline_approve_from_queue(self):
        entry = self._raise_entry()
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("decide_litigation_entry", args=[entry.litigation_id]),
            {"entry_id": entry.litigation_id, "decision": "APPROVE",
             "decision_notes": "Approved from hub."},
        )
        self.assertRedirects(response, reverse("approval_queue"))
        entry.refresh_from_db()
        self.assertEqual(entry.status, LitigationEntry.Status.APPROVED)

    def test_inline_reject_from_queue(self):
        entry = self._raise_entry()
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("decide_litigation_entry", args=[entry.litigation_id]),
            {"entry_id": entry.litigation_id, "decision": "REJECT",
             "decision_notes": "Rejected from hub."},
        )
        self.assertRedirects(response, reverse("approval_queue"))
        entry.refresh_from_db()
        self.assertEqual(entry.status, LitigationEntry.Status.REJECTED)

    def test_litigation_tab_deep_link(self):
        self._raise_entry()
        self.client.force_login(self.manager)
        response = self.client.get(self.approval_url, {"tab": "litigation"})
        body = response.content.decode()
        # Deep link lands on and keeps the litigation tab active.
        self.assertIn("?tab=litigation", body)
        self.assertIn("Litigation Entries", body)
