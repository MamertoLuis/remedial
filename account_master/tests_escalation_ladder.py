"""Tests for the notice escalation ladder (change notice-escalation-ladder).

Covers: the three ladder models + seeding migration + admin pages (section 1),
the escalation service core (section 2), the snapshot hook (section 3), the
arrangement hook (section 4), promise-to-pay pause (section 5), the overdue
alert rule (section 6) and the officer-facing views (section 7).
"""
import datetime
import importlib
from decimal import Decimal

import django.apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from account_master.models import (
    Alert,
    AlertRule,
    Borrower,
    CollectionActivityLog,
    EscalationStage,
    EscalationState,
    LoanAccount,
    Notice,
    RemedialStrategy,
)
from account_master.services.alert_service import AlertService
from account_master.services.escalation_service import (
    close_escalation,
    get_open_state,
    has_pending_ptp,
    issue_notice,
    pause_escalation,
    recommend_terminal,
    resume_escalation,
    start_escalation,
    sync_escalation_on_snapshot,
    sync_pause_state,
)
from compromise_agreement.models import CompromiseAgreement

User = get_user_model()


def _today():
    return timezone.now().date()


def _borrower(borrower_id="B-ESC-001", **overrides):
    defaults = {
        "borrower_id": borrower_id,
        "borrower_type": "PERSON",
        "full_name": "Escalation Borrower",
        "primary_address": "1 Ladder St",
    }
    defaults.update(overrides)
    return Borrower.objects.create(**defaults)


def _account(loan_id="L-ESC-001", status="PERFORMING", **overrides):
    defaults = {
        "loan_id": loan_id,
        "borrower": _borrower(borrower_id=f"B-{loan_id}"),
        "booking_date": datetime.date(2023, 1, 1),
        "maturity_date": datetime.date(2026, 1, 1),
        "original_principal": Decimal("10000.00"),
        "interest_rate": Decimal("12.00"),
        "loan_type": "Personal",
        "loan_security": "UNSECURED",
        "status": status,
    }
    defaults.update(overrides)
    return LoanAccount.objects.create(**defaults)


class EscalationModelTests(TestCase):
    """Tasks 1.1 - 1.3: models, uniqueness and filtering."""

    def setUp(self):
        self.account = _account()

    def test_escalation_stage_fields_and_ordering(self):
        stage = EscalationStage.objects.create(
            stage_no=10, label="Test Stage", duration_days=45, is_terminal=False
        )
        self.assertEqual(stage.stage_no, 10)
        self.assertEqual(stage.duration_days, 45)
        self.assertFalse(stage.is_terminal)
        self.assertEqual(str(stage), "10. Test Stage")
        # Ordered by stage_no
        stages = list(EscalationStage.objects.all())
        self.assertEqual(stages, sorted(stages, key=lambda s: s.stage_no))

    def test_one_open_escalation_state_per_account(self):
        first = start_escalation(self.account)[0]
        self.assertEqual(EscalationState.objects.filter(account=self.account).count(), 1)
        # Creating a second open state violates the partial unique constraint.
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                EscalationState.objects.create(
                    account=self.account,
                    current_stage=EscalationStage.objects.order_by("stage_no").first(),
                    stage_started_on=_today(),
                    status=EscalationState.Status.PENDING,
                )
        self.assertEqual(EscalationState.objects.filter(account=self.account).count(), 1)
        self.assertTrue(first.is_open)

    def test_closed_state_does_not_block_a_new_open_state(self):
        start_escalation(self.account)
        close_escalation(self.account, "cured")
        state, created = start_escalation(self.account)
        self.assertTrue(created)
        self.assertEqual(state.status, EscalationState.Status.PENDING)

    def test_notice_creation_and_account_filtering(self):
        stage = EscalationStage.objects.order_by("stage_no").first()
        other_account = _account(loan_id="L-ESC-002")
        Notice.objects.create(
            account=self.account, stage=stage, issued_on=_today(), method="Letter"
        )
        Notice.objects.create(
            account=self.account, stage=stage, issued_on=_today(), method="Email"
        )
        Notice.objects.create(
            account=other_account, stage=stage, issued_on=_today(), method="SMS"
        )

        self.assertEqual(Notice.objects.filter(account=self.account).count(), 2)
        self.assertEqual(Notice.objects.filter(account=other_account).count(), 1)
        self.assertEqual(Notice.objects.filter(stage=stage).count(), 3)
        self.assertEqual(Notice.objects.count(), 3)

    def test_data_migration_seeds_fixed_ladder(self):
        """Task 1.4: migrate seeds exactly the expected stage rows."""
        expected = [
            ("First Demand", 30, False),
            ("Warning", 30, False),
            ("Legal Intent", 30, True),
        ]
        stages = list(EscalationStage.objects.order_by("stage_no"))
        self.assertEqual(len(stages), 3)
        for stage, (label, duration, terminal) in zip(stages, expected):
            self.assertEqual(stage.label, label)
            self.assertEqual(stage.duration_days, duration)
            self.assertEqual(stage.is_terminal, terminal)

    def test_data_migration_seeding_is_idempotent(self):
        migration = importlib.import_module(
            "account_master.migrations.0004_seed_escalation_stages"
        )
        migration.seed_escalation_stages(django.apps.apps, None)
        migration.seed_escalation_stages(django.apps.apps, None)
        self.assertEqual(EscalationStage.objects.count(), 3)


class EscalationAdminTests(TestCase):
    """Task 1.5: admin pages load for the three models."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.force_login(self.user)
        _account()

    def test_admin_pages_load(self):
        for path in [
            "/admin/account_master/escalationstage/",
            "/admin/account_master/escalationstage/add/",
            "/admin/account_master/escalationstate/",
            "/admin/account_master/notice/",
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, path)


class EscalationServiceCoreTests(TestCase):
    """Tasks 2.1 - 2.4: start, issue/advance, terminal recommendation, close."""

    def setUp(self):
        self.account = _account(status="PAST_DUE")

    def test_start_escalation_creates_pending_at_first_stage(self):
        state, created = start_escalation(self.account)
        self.assertTrue(created)
        self.assertEqual(state.status, EscalationState.Status.PENDING)
        self.assertEqual(state.current_stage.stage_no, 1)
        self.assertIsNone(state.next_notice_due)

    def test_start_escalation_does_not_duplicate(self):
        start_escalation(self.account)
        state, created = start_escalation(self.account)
        self.assertFalse(created)
        self.assertEqual(EscalationState.objects.filter(account=self.account).count(), 1)

    def test_issue_notice_advances_non_terminal(self):
        start_escalation(self.account)
        notice, state = issue_notice(
            self.account,
            EscalationStage.objects.get(stage_no=1),
            "Letter",
        )
        # Notice recorded against stage 1
        self.assertEqual(Notice.objects.filter(account=self.account).count(), 1)
        self.assertEqual(notice.stage.stage_no, 1)
        # Advanced to stage 2, ACTIVE, due date from the new stage's duration.
        self.assertEqual(state.status, EscalationState.Status.ACTIVE)
        self.assertEqual(state.current_stage.stage_no, 2)
        self.assertEqual(
            state.next_notice_due,
            notice.issued_on
            + datetime.timedelta(days=EscalationStage.objects.get(stage_no=2).duration_days),
        )
        self.assertEqual(state.stage_started_on, notice.issued_on)

    def test_issue_notice_at_terminal_stage_closes(self):
        start_escalation(self.account)
        # Walk to the terminal stage (stage 3).
        issue_notice(self.account, EscalationStage.objects.get(stage_no=1), "Letter")
        issue_notice(self.account, EscalationStage.objects.get(stage_no=2), "Letter")

        notice, state = issue_notice(
            self.account, EscalationStage.objects.get(stage_no=3), "Letter"
        )
        self.assertEqual(Notice.objects.filter(account=self.account).count(), 3)
        self.assertIsNone(state)
        closed = EscalationState.objects.get(account=self.account)
        self.assertEqual(closed.status, EscalationState.Status.CLOSED)
        self.assertEqual(closed.closed_reason, EscalationState.CloseReason.TERMINAL)
        self.assertIsNone(closed.next_notice_due)

    def test_issue_notice_rejects_mismatched_stage(self):
        start_escalation(self.account)
        with self.assertRaises(ValueError):
            issue_notice(self.account, EscalationStage.objects.get(stage_no=2), "Letter")

    def test_issue_notice_requires_open_state(self):
        with self.assertRaises(ValueError):
            issue_notice(self.account, EscalationStage.objects.get(stage_no=1), "Letter")

    def test_recommend_terminal_creates_legal_strategy_and_closes(self):
        start_escalation(self.account)
        strategy = recommend_terminal(self.account, "Legal Action")
        self.assertEqual(strategy.strategy_type, "Legal Action")
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)
        state = EscalationState.objects.get(account=self.account)
        self.assertEqual(state.status, EscalationState.Status.CLOSED)
        self.assertEqual(state.closed_reason, EscalationState.CloseReason.TERMINAL)

    def test_recommend_terminal_rejects_unknown_strategy_type(self):
        start_escalation(self.account)
        with self.assertRaises(ValueError):
            recommend_terminal(self.account, "Write-Off")

    def test_recommend_terminal_upholds_one_active_strategy_invariant(self):
        start_escalation(self.account)
        RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=_today(),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )
        recommend_terminal(self.account, "Foreclosure")
        self.assertEqual(
            RemedialStrategy.objects.filter(
                account=self.account, strategy_status=RemedialStrategy.StrategyStatus.ACTIVE
            ).count(),
            1,
        )
        self.assertTrue(self.account.has_foreclosure_strategy)

    def test_close_escalation_reasons(self):
        for reason in ["cured", "arrangement", "terminal"]:
            with self.subTest(reason=reason):
                account = _account(loan_id=f"L-ESC-{reason}")
                start_escalation(account)
                closed = close_escalation(account, reason)
                self.assertEqual(closed.status, EscalationState.Status.CLOSED)
                self.assertEqual(closed.closed_reason, reason)
                # No further notice is scheduled.
                self.assertIsNone(closed.next_notice_due)
                self.assertIsNone(get_open_state(account))

    def test_close_escalation_is_noop_without_open_state(self):
        self.assertIsNone(close_escalation(self.account, "cured"))


class EscalationSnapshotHookTests(TestCase):
    """Task 3.1: idempotent snapshot coupling through the service and main.py."""

    def setUp(self):
        self.account = _account(status="PERFORMING")

    def test_delinquent_snapshot_creates_pending(self):
        sync_escalation_on_snapshot(self.account, "PAST_DUE")
        state = get_open_state(self.account)
        self.assertIsNotNone(state)
        self.assertEqual(state.status, EscalationState.Status.PENDING)
        self.assertEqual(state.current_stage.stage_no, 1)

    def test_repeat_snapshots_do_not_duplicate(self):
        sync_escalation_on_snapshot(self.account, "PAST_DUE")
        sync_escalation_on_snapshot(self.account, "NPL")
        sync_escalation_on_snapshot(self.account, "PAST_DUE")
        self.assertEqual(EscalationState.objects.filter(account=self.account).count(), 1)

    def test_performing_snapshot_closes_open_active_state_with_cured(self):
        start_escalation(self.account)
        issue_notice(self.account, EscalationStage.objects.get(stage_no=1), "Letter")
        self.assertEqual(get_open_state(self.account).status, EscalationState.Status.ACTIVE)

        sync_escalation_on_snapshot(self.account, "PERFORMING")
        state = EscalationState.objects.get(account=self.account)
        self.assertEqual(state.status, EscalationState.Status.CLOSED)
        self.assertEqual(state.closed_reason, EscalationState.CloseReason.CURED)
        # Stage is NOT advanced by the cure/cure snapshot.
        self.assertEqual(state.current_stage.stage_no, 2)

    def test_new_delinquency_episode_after_cure_starts_fresh_ladder(self):
        start_escalation(self.account)
        sync_escalation_on_snapshot(self.account, "PERFORMING")
        self.assertIsNone(get_open_state(self.account))

        sync_escalation_on_snapshot(self.account, "NPL")
        state = get_open_state(self.account)
        self.assertEqual(state.status, EscalationState.Status.PENDING)
        self.assertEqual(state.current_stage.stage_no, 1)

    def test_snapshot_path_in_main_creates_ladder(self):
        """Integration: upsert_exposure → sync hook in services/main.py."""
        from account_master.services import upsert_exposure, upsert_delinquency_status

        upsert_exposure(
            account=self.account,
            as_of_date=_today(),
            defaults={
                "principal_outstanding": Decimal("5000.00"),
                "accrued_interest": Decimal("100.00"),
                "accrued_penalty": Decimal("0.00"),
                "days_past_due": 45,
            },
        )
        state = get_open_state(self.account)
        self.assertIsNotNone(state)
        self.assertEqual(state.status, EscalationState.Status.PENDING)

        # Cure it through the snapshot path: open state closes with "cured".
        issue_notice(self.account, state.current_stage, "Letter")
        upsert_delinquency_status(
            account=self.account,
            as_of_date=_today(),
            defaults={"days_past_due": 0, "classification": "C"},
        )
        closed = EscalationState.objects.get(account=self.account)
        self.assertEqual(closed.status, EscalationState.Status.CLOSED)
        self.assertEqual(closed.closed_reason, EscalationState.CloseReason.CURED)


class EscalationArrangementHookTests(TestCase):
    """Task 4.1: approved arrangement closes the ladder."""

    def setUp(self):
        self.account = _account(status="NPL")
        start_escalation(self.account)
        issue_notice(self.account, EscalationStage.objects.get(stage_no=1), "Letter")
        self.assertEqual(get_open_state(self.account).status, EscalationState.Status.ACTIVE)

    def test_active_compromise_agreement_closes_with_arrangement(self):
        strategy = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Compromise",
            strategy_start_date=_today(),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )
        CompromiseAgreement.objects.create(
            strategy=strategy,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("8000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="ACTIVE",
        )

        # A snapshot (still delinquent) runs the arrangement check.
        sync_escalation_on_snapshot(self.account, "NPL")
        state = EscalationState.objects.get(account=self.account)
        self.assertEqual(state.status, EscalationState.Status.CLOSED)
        self.assertEqual(state.closed_reason, EscalationState.CloseReason.ARRANGEMENT)
        self.assertIsNone(state.next_notice_due)
        self.assertIsNone(get_open_state(self.account))

    def test_active_restructuring_strategy_closes_with_arrangement(self):
        RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Restructuring",
            strategy_start_date=_today(),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )
        sync_escalation_on_snapshot(self.account, "NPL")
        state = EscalationState.objects.get(account=self.account)
        self.assertEqual(state.status, EscalationState.Status.CLOSED)
        self.assertEqual(state.closed_reason, EscalationState.CloseReason.ARRANGEMENT)


class EscalationPtpPauseTests(TestCase):
    """Task 5.1: ladder pauses only while a promise to pay is pending."""

    def _add_ptp(self, account, days_offset):
        return CollectionActivityLog.objects.create(
            account=account,
            activity_date=_today(),
            activity_type="Negotiation",
            remarks="Promise to pay",
            staff_assigned="Agent",
            promise_to_pay_amount=Decimal("1000.00"),
            promise_to_pay_date=_today() + datetime.timedelta(days=days_offset),
        )

    def _active_state(self):
        start_escalation(self.account)
        issue_notice(self.account, EscalationStage.objects.get(stage_no=1), "Letter")
        state = get_open_state(self.account)
        self.assertEqual(state.status, EscalationState.Status.ACTIVE)
        return state

    def setUp(self):
        self.account = _account(status="PAST_DUE")

    def test_has_pending_ptp_detection(self):
        self.assertFalse(has_pending_ptp(self.account))
        ptp = self._add_ptp(self.account, days_offset=10)
        self.assertTrue(has_pending_ptp(self.account))
        # Promise date reached → no longer pending.
        ptp.promise_to_pay_date = _today() - datetime.timedelta(days=1)
        ptp.save()
        self.assertFalse(has_pending_ptp(self.account))

    def test_pending_promise_pauses(self):
        state = self._active_state()
        stage_before = state.current_stage
        self._add_ptp(self.account, days_offset=10)
        synced = sync_pause_state(self.account)
        self.assertEqual(synced.status, EscalationState.Status.PAUSED)
        # Same stage, just paused.
        self.assertEqual(synced.current_stage, stage_before)

    def test_resolved_promise_resumes_active_at_same_stage(self):
        state = self._active_state()
        stage_before = state.current_stage
        ptp = self._add_ptp(self.account, days_offset=10)
        sync_pause_state(self.account)
        self.assertEqual(get_open_state(self.account).status, EscalationState.Status.PAUSED)

        # Promise is resolved: its date passes (honored or broken).
        ptp.promise_to_pay_date = _today() - datetime.timedelta(days=1)
        ptp.save()
        synced = sync_pause_state(self.account)
        self.assertEqual(synced.status, EscalationState.Status.ACTIVE)
        # Resumes at the SAME stage and never auto-advances.
        self.assertEqual(synced.current_stage, stage_before)

    def test_explicit_pause_resume_transitions(self):
        state = self._active_state()
        self.assertIsNotNone(pause_escalation(self.account))
        self.assertEqual(get_open_state(self.account).status, EscalationState.Status.PAUSED)
        self.assertIsNotNone(resume_escalation(self.account))
        self.assertEqual(get_open_state(self.account).status, EscalationState.Status.ACTIVE)

    def test_snapshot_sync_applies_pause(self):
        self._active_state()
        self._add_ptp(self.account, days_offset=10)
        sync_escalation_on_snapshot(self.account, "PAST_DUE")
        self.assertEqual(get_open_state(self.account).status, EscalationState.Status.PAUSED)

    def test_honored_promise_does_not_clear_ladder_or_stage(self):
        state = self._active_state()
        stage_before = state.current_stage
        ptp = self._add_ptp(self.account, days_offset=10)
        sync_pause_state(self.account)

        # Promise honored (date reached) but the delinquency is NOT cleared.
        ptp.promise_to_pay_date = _today() - datetime.timedelta(days=1)
        ptp.save()
        synced = sync_pause_state(self.account)
        # Stage unchanged; ladder not reset or advanced.
        self.assertEqual(synced.current_stage, stage_before)
        self.assertEqual(synced.status, EscalationState.Status.ACTIVE)
        self.assertEqual(EscalationState.objects.filter(account=self.account).count(), 1)


class EscalationAlertTests(TestCase):
    """Tasks 6.1 & 6.2: NOTICE_OVERDUE alert with no auto-advance."""

    def setUp(self):
        self.account = _account(loan_id="L-ESC-ALERT-1", status="PAST_DUE")
        self.other = _account(loan_id="L-ESC-ALERT-2", status="PAST_DUE")
        self.rule = AlertRule.objects.create(
            name="Next Notice Overdue Rule",
            description="Alert when an escalation notice is overdue",
            rule_type=AlertRule.RuleType.NOTICE_OVERDUE,
            condition_value=Decimal("0.00"),
            is_active=True,
            alert_type=Alert.AlertType.WARNING,
            severity=Alert.Severity.MEDIUM,
        )

    def _active_state(self, account):
        start_escalation(account)
        issue_notice(account, EscalationStage.objects.get(stage_no=1), "Letter")
        return get_open_state(account)

    def test_overdue_notice_raises_alert_and_on_time_state_produces_none(self):
        overdue = self._active_state(self.account)
        overdue.next_notice_due = _today() - datetime.timedelta(days=1)
        overdue.save()

        on_time = self._active_state(self.other)
        on_time.next_notice_due = _today() + datetime.timedelta(days=10)
        on_time.save()

        alerts = AlertService.check_alert_rules()
        account_alerts = [a for a in alerts if a.entity_id == self.account.loan_id]
        other_alerts = [a for a in alerts if a.entity_id == self.other.loan_id]

        self.assertEqual(len(account_alerts), 1)
        self.assertTrue(
            account_alerts[0].title.startswith("Next Notice Overdue"),
            account_alerts[0].title,
        )
        self.assertEqual(len(other_alerts), 0)

    def test_overdue_alert_never_advances_the_stage(self):
        state = self._active_state(self.account)
        stage_before = state.current_stage
        state.next_notice_due = _today() - datetime.timedelta(days=5)
        state.save()

        AlertService.check_alert_rules()

        state.refresh_from_db()
        self.assertEqual(state.current_stage, stage_before)
        self.assertEqual(state.status, EscalationState.Status.ACTIVE)


class EscalationViewTests(TestCase):
    """Tasks 7.1 & 7.2: officer-facing views and templates."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="officer", password="password")
        self.client.force_login(self.user)
        self.account = _account(status="PAST_DUE")
        self.ladder_url = reverse(
            "escalation_ladder_detail", args=[self.account.loan_id]
        )
        self.issue_url = reverse(
            "issue_escalation_notice", args=[self.account.loan_id]
        )

    def test_ladder_detail_requires_login(self):
        anonymous = Client()
        response = anonymous.get(self.ladder_url)
        self.assertNotEqual(response.status_code, 200)

    def test_ladder_detail_returns_ladder_context(self):
        start_escalation(self.account)
        response = self.client.get(self.ladder_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/escalation_ladder.html")
        self.assertEqual(response.context["account"], self.account)
        state = response.context["escalation_state"]
        self.assertEqual(state.account, self.account)
        self.assertIn("notices", response.context)

    def test_issue_notice_action_records_notice_and_advances(self):
        start_escalation(self.account)
        response = self.client.post(
            self.issue_url, {"method": Notice.Method.LETTER}
        )
        self.assertRedirects(response, self.ladder_url)
        self.assertEqual(Notice.objects.filter(account=self.account).count(), 1)
        state = get_open_state(self.account)
        self.assertEqual(state.status, EscalationState.Status.ACTIVE)
        self.assertEqual(state.current_stage.stage_no, 2)

    def test_issue_notice_page_renders_with_current_state(self):
        start_escalation(self.account)
        response = self.client.get(self.issue_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/issue_notice.html")
        self.assertEqual(response.context["escalation_state"].account, self.account)

    def test_ladder_smoke_renders_with_account_state(self):
        start_escalation(self.account)
        response = self.client.get(self.ladder_url)
        self.assertContains(response, self.account.loan_id)
        self.assertContains(response, "First Demand")
