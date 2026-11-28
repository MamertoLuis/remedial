"""Tests for the remedial strategy framework change.

Sections: 1 - data model foundation (1.1-1.7), 2 - catalog seeding (2.1),
3 - strategy service (3.1-3.5), 4 - lifecycle gates & escalation (4.1-4.4),
5 - view permission gating (5.x), 6 - end-to-end integration (6.1).
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from account_master.forms import CollectionActivityLogForm
from account_master.models import (
    Borrower,
    Collateral,
    CollectionActivityLog,
    EscalationState,
    Guarantor,
    LoanAccount,
    RemedialStrategy,
    StrategyAction,
    StrategyActionCatalogEntry,
    StrategyApproval,
    StrategyAssessment,
)
from account_master.services import (
    escalation_service,
    litigation_service,
    strategy_service,
)
from account_master.services.main import create_collection_activity
from compromise_agreement.models import CompromiseAgreement

User = get_user_model()


def _today():
    return timezone.now().date()


def make_account(*, loan_id="L001", status="NPL", loan_security="UNSECURED"):
    borrower = Borrower.objects.create(
        borrower_id=f"B-{loan_id}",
        full_name="John Doe",
        primary_address="123 Main St",
        mobile="1234567890",
    )
    return LoanAccount.objects.create(
        loan_id=loan_id,
        borrower=borrower,
        booking_date=datetime.date(2023, 1, 1),
        maturity_date=datetime.date(2026, 1, 1),
        original_principal=Decimal("10000.00"),
        interest_rate=Decimal("5.00"),
        loan_type="Personal",
        loan_security=loan_security,
        status=status,
    )


def make_users():
    officer = User.objects.create_user(
        username="officer", password="pass", role=User.Role.ACCOUNT_OFFICER
    )
    manager = User.objects.create_user(
        username="manager", password="pass", role=User.Role.MANAGER
    )
    board = User.objects.create_user(
        username="board", password="pass", role=User.Role.BOARD_MEMBER
    )
    return officer, manager, board


def make_strategy(account, strategy_type="Intensive Collection", status="ACTIVE"):
    return RemedialStrategy.objects.create(
        account=account,
        strategy_type=strategy_type,
        strategy_start_date=_today(),
        strategy_status=status,
    )


def make_assessment(
    strategy, officer, *, rationale="Borrower unable to pay due to business slowdown"
):
    return StrategyAssessment.objects.create(
        strategy=strategy,
        as_of_date=strategy.strategy_start_date,
        officer_rationale=rationale,
        financial_condition="WEAK",
        financial_condition_note="Cash flow negative",
        willingness_to_pay="MEDIUM",
        willingness_note="Committed verbally",
        recovery_outlook="LOW",
        recovery_assessment_note="No known assets",
        expected_recovery=Decimal("1000.00"),
        created_by=officer,
        updated_by=officer,
    )


def base_assessment(**overrides):
    data = {
        "as_of_date": _today(),
        "officer_rationale": "Borrower unable to pay due to business slowdown",
        "financial_condition": "WEAK",
        "financial_condition_note": "Cash flow negative",
        "willingness_to_pay": "MEDIUM",
        "willingness_note": "Committed verbally",
        "recovery_outlook": "LOW",
        "recovery_assessment_note": "No known assets",
        "expected_recovery": Decimal("1000.00"),
    }
    data.update(overrides)
    return data


# ===========================================================================
# 1. Data model foundation
# ===========================================================================


class EvidenceLinkTests(TestCase):
    """Strategy action evidence links and the one-step log-and-execute path."""

    def setUp(self):
        self.officer, self.manager, _board = make_users()
        self.account = make_account(loan_id="L-EVID")
        self.strategy = make_strategy(self.account)
        self.entry = StrategyActionCatalogEntry.objects.create(
            strategy_type="Intensive Collection",
            code="IC-EVID",
            name="Call",
            ordering=1,
            requires_approval=False,
        )
        self.action = StrategyAction.objects.create(
            catalog_entry=self.entry,
            strategy=self.strategy,
            status=StrategyAction.ActionStatus.SELECTED,
            created_by=self.officer,
            updated_by=self.officer,
        )

    def _link(self, *, account=None, action=None):
        return create_collection_activity(
            account=account or self.account,
            activity_date=_today(),
            activity_type="Call",
            remarks="Called borrower",
            action=action if action is not None else self.action,
        )

    def test_activity_form_limits_choices_to_active_strategy_actions(self):
        # Form exposes the active strategy's SELECTED action.
        form = CollectionActivityLogForm(account=self.account)
        self.assertEqual(
            list(form.fields["action"].queryset.values_list("pk", flat=True)),
            [self.action.pk],
        )
        # An account with no ACTIVE strategy offers an empty choice set.
        empty_account = make_account(loan_id="L-NOSTRAT")
        form = CollectionActivityLogForm(account=empty_account)
        self.assertEqual(form.fields["action"].queryset.count(), 0)
        # An action of an exited strategy is not offered.
        cancelled = make_strategy(self.account, status="CANCELLED")
        StrategyAction.objects.create(
            catalog_entry=self.entry,
            strategy=cancelled,
            status=StrategyAction.ActionStatus.SELECTED,
            created_by=self.officer,
            updated_by=self.officer,
        )
        form = CollectionActivityLogForm(account=self.account)
        self.assertEqual(
            list(form.fields["action"].queryset.values_list("pk", flat=True)),
            [self.action.pk],
        )

    def test_same_account_rule_rejects_cross_account_link(self):
        other = make_account(loan_id="L-OTHER")
        with self.assertRaises(ValidationError):
            self._link(account=other)
        self.assertFalse(
            CollectionActivityLog.objects.filter(action=self.action).exists()
        )

    def test_link_to_exited_strategy_is_rejected(self):
        cancelled = make_strategy(self.account, status="CANCELLED")
        other_action = StrategyAction.objects.create(
            catalog_entry=self.entry,
            strategy=cancelled,
            status=StrategyAction.ActionStatus.SELECTED,
            created_by=self.officer,
            updated_by=self.officer,
        )
        with self.assertRaises(ValidationError):
            self._link(action=other_action)
        self.assertFalse(
            CollectionActivityLog.objects.filter(action=other_action).exists()
        )

    def test_valid_link_is_recorded(self):
        activity = self._link()
        self.assertEqual(activity.action, self.action)

    def test_linking_pure_evidence_does_not_execute_action(self):
        self._link()
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.SELECTED)

    def test_one_step_log_and_execute(self):
        result = strategy_service.execute_action_and_log_activity(
            action=self.action,
            outcome="Borrower promised payment",
            activity_type="Call",
            remarks="Called and agreed follow-up",
            officer=self.officer,
        )
        activity = result["activity"]
        executed = result["action"]
        self.assertEqual(activity.action, self.action)
        self.assertEqual(executed.status, StrategyAction.ActionStatus.EXECUTED)
        self.assertEqual(executed.outcome, "Borrower promised payment")

    def test_one_step_rejects_unapproved_gated_action(self):
        gated_entry = StrategyActionCatalogEntry.objects.create(
            strategy_type="Intensive Collection",
            code="IC-GATED-EVID",
            name="Commitment",
            ordering=2,
            requires_approval=True,
        )
        gated = StrategyAction.objects.create(
            catalog_entry=gated_entry,
            strategy=self.strategy,
            status=StrategyAction.ActionStatus.SELECTED,
            created_by=self.officer,
            updated_by=self.officer,
        )
        with self.assertRaises(ValidationError):
            strategy_service.execute_action_and_log_activity(
                action=gated,
                outcome="commitment",
                activity_type="Negotiation",
                remarks="attempted",
                officer=self.officer,
            )
        self.assertFalse(
            CollectionActivityLog.objects.filter(action=gated).exists()
        )
        gated.refresh_from_db()
        self.assertEqual(gated.status, StrategyAction.ActionStatus.SELECTED)

    def test_view_log_execute_creates_activity_and_executes_action(self):
        self.client.force_login(self.officer)
        response = self.client.post(
            reverse(
                "remedial_strategy_detail",
                args=[self.account.loan_id, self.strategy.strategy_id],
            ),
            {
                "action": "log_execute",
                "action_id": self.action.action_id,
                "outcome": "Follow-up scheduled",
                "activity_type": "Call",
                "remarks": "Borrower asked for more time",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        activity = CollectionActivityLog.objects.get(action=self.action)
        self.assertEqual(activity.activity_type, "Call")
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.EXECUTED)
        self.assertEqual(self.action.outcome, "Follow-up scheduled")


class GuarantorModelTest(TestCase):
    def test_create_and_read_guarantor(self):
        account = make_account()
        guarantor = Guarantor.objects.create(
            account=account,
            full_name="Jane Surety",
            identity="ID-777777",
            guarantee_amount=Decimal("5000.00"),
            guarantee_type=Guarantor.GuaranteeType.SOLIDARY,
            is_enforceable=True,
        )
        fetched = Guarantor.objects.get(pk=guarantor.guarantor_id)
        self.assertEqual(fetched.account, account)
        self.assertEqual(fetched.full_name, "Jane Surety")
        self.assertEqual(fetched.guarantee_amount, Decimal("5000.00"))
        self.assertEqual(fetched.guarantee_type, "SOLIDARY")
        self.assertTrue(fetched.is_enforceable)
        self.assertIn("Jane Surety", str(fetched))


class CollateralModelTest(TestCase):
    def test_create_and_read_collateral(self):
        account = make_account()
        collateral = Collateral.objects.create(
            account=account,
            description="Residential lot in Quezon City",
            collateral_type="REAL_ESTATE",
            appraised_value=Decimal("750000.00"),
            as_of_date=_today(),
        )
        fetched = Collateral.objects.get(pk=collateral.collateral_id)
        self.assertEqual(fetched.account, account)
        self.assertEqual(fetched.collateral_type, "REAL_ESTATE")
        self.assertEqual(fetched.appraised_value, Decimal("750000.00"))
        self.assertEqual(fetched.as_of_date, _today())


class StrategyAssessmentModelTest(TestCase):
    def test_assessment_snapshot_records_seven_inputs(self):
        account = make_account()
        officer, _, _ = make_users()
        strategy = make_strategy(account)
        assessment = make_assessment(strategy, officer)
        fetched = StrategyAssessment.objects.get(pk=assessment.assessment_id)
        self.assertEqual(fetched.strategy, strategy)
        self.assertEqual(fetched.officer_rationale, assessment.officer_rationale)
        self.assertEqual(fetched.financial_condition, "WEAK")
        self.assertEqual(fetched.willingness_to_pay, "MEDIUM")
        self.assertEqual(fetched.recovery_outlook, "LOW")
        self.assertEqual(fetched.expected_recovery, Decimal("1000.00"))

    def test_prior_snapshot_remains_unchanged(self):
        """Two recommendations keep two distinct assessments (spec 1.3)."""
        account = make_account()
        officer, _, _ = make_users()
        strategy1 = make_strategy(account, strategy_type="Intensive Collection")
        assessment1 = make_assessment(strategy1, officer)
        # A second recommendation on the same account is its own snapshot.
        strategy2 = make_strategy(account, strategy_type="Restructuring")
        make_assessment(strategy2, officer, rationale="Second recommendation")
        assessment1.refresh_from_db()
        self.assertEqual(StrategyAssessment.objects.count(), 2)
        self.assertEqual(
            assessment1.officer_rationale,
            "Borrower unable to pay due to business slowdown",
        )
        self.assertEqual(
            StrategyAssessment.objects.get(strategy=strategy2).officer_rationale,
            "Second recommendation",
        )


class StrategyActionCatalogEntryModelTest(TestCase):
    def test_six_strategy_types_expose_catalog_entries(self):
        entries = StrategyActionCatalogEntry.objects.all()
        self.assertGreater(entries.count(), 0)
        types_with_entries = set(entries.values_list("strategy_type", flat=True))
        self.assertEqual(
            types_with_entries,
            {
                "Intensive Collection",
                "Restructuring",
                "Compromise",
                "Foreclosure",
                "Legal Action",
                "Write-Off",
            },
        )

    def test_catalog_entry_requires_approval_flag(self):
        entry = StrategyActionCatalogEntry.objects.get(code="IC-CALL")
        self.assertFalse(entry.requires_approval)
        gated = StrategyActionCatalogEntry.objects.get(code="WO-APPROVAL")
        self.assertTrue(gated.requires_approval)


class StrategyActionModelTest(TestCase):
    def setUp(self):
        self.account = make_account()
        self.officer, self.manager, _ = make_users()
        self.strategy = make_strategy(self.account)
        self.gated = StrategyActionCatalogEntry.objects.get(code="WO-APPROVAL")
        self.nongated = StrategyActionCatalogEntry.objects.get(code="IC-CALL")

    def test_non_gated_action_executes_directly(self):
        action = StrategyAction.objects.create(
            catalog_entry=self.nongated,
            strategy=self.strategy,
            created_by=self.officer,
            updated_by=self.officer,
        )
        self.assertEqual(action.status, StrategyAction.ActionStatus.SELECTED)
        action.execute(outcome="Borrower promised payment next week")
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.EXECUTED)
        self.assertEqual(action.outcome, "Borrower promised payment next week")
        self.assertIsNotNone(action.executed_on)

    def test_gated_status_machine_select_to_approved_to_executed(self):
        action = StrategyAction.objects.create(
            catalog_entry=self.gated,
            strategy=self.strategy,
            status=StrategyAction.ActionStatus.PENDING_APPROVAL,
            created_by=self.officer,
            updated_by=self.officer,
        )
        # Blocked before approval
        with self.assertRaises(ValidationError):
            action.execute(outcome="Too early")
        action.mark_approved()
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.APPROVED)
        action.execute(outcome="Booked")
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.EXECUTED)

    def test_gated_rejection_keeps_action_unexecuted(self):
        action = StrategyAction.objects.create(
            catalog_entry=self.gated,
            strategy=self.strategy,
            status=StrategyAction.ActionStatus.PENDING_APPROVAL,
            created_by=self.officer,
            updated_by=self.officer,
        )
        action.mark_rejected()
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.REJECTED)
        with self.assertRaises(ValidationError):
            action.execute(outcome="After rejection")


class StrategyApprovalModelTest(TestCase):
    def setUp(self):
        self.account = make_account()
        self.officer, self.manager, _ = make_users()
        self.strategy = make_strategy(self.account)
        self.gated = StrategyActionCatalogEntry.objects.get(code="WO-APPROVAL")

    def test_only_approved_record_releases_gated_action_and_conditions_stored(self):
        action = StrategyAction.objects.create(
            catalog_entry=self.gated,
            strategy=self.strategy,
            status=StrategyAction.ActionStatus.PENDING_APPROVAL,
            created_by=self.officer,
            updated_by=self.officer,
        )
        StrategyApproval.objects.create(
            action=action,
            approver=self.manager,
            decision=StrategyApproval.Decision.APPROVED,
            comments="Approved",
            conditions="Subject to board endorsement within 10 days",
            created_by=self.manager,
            updated_by=self.manager,
        )
        approval = action.approvals.get()
        self.assertEqual(approval.decision, "APPROVED")
        self.assertEqual(approval.approver, self.manager)
        self.assertEqual(
            approval.conditions, "Subject to board endorsement within 10 days"
        )
        action.mark_approved()
        action.execute(outcome="Booked")
        self.assertEqual(action.status, StrategyAction.ActionStatus.EXECUTED)


class CompromiseAgreementStatusTest(TestCase):
    def test_unsuccessful_status_is_available_and_existing_active_preserved(self):
        account = make_account()
        officer, _, _ = make_users()
        strategy = make_strategy(account, strategy_type="Compromise", status="ACTIVE")
        legacy = CompromiseAgreement.objects.create(
            strategy=strategy,
            account=account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("5000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="ACTIVE",
            created_by=officer,
            updated_by=officer,
        )
        self.assertEqual(legacy.status, "ACTIVE")  # existing behavior preserved
        legacy.status = CompromiseAgreement.CompromiseStatus.UNSUCCESSFUL
        legacy.save()
        legacy.refresh_from_db()
        self.assertEqual(legacy.status, "UNSUCCESSFUL")
        self.assertIn(
            CompromiseAgreement.CompromiseStatus.PENDING_APPROVAL,
            CompromiseAgreement.CompromiseStatus.values,
        )


# ===========================================================================
# 2. Catalog seeding
# ===========================================================================


class CatalogSeedingTest(TestCase):
    """Task 2.1: seeded counts match the proposal action lists; gating per D3."""

    PROPOSAL_COUNTS = {
        "Intensive Collection": 7,
        "Restructuring": 7,
        "Compromise": 5,
        "Foreclosure": 5,
        "Legal Action": 6,
        "Write-Off": 4,
    }

    def test_seeded_counts_match_proposal_lists(self):
        for strategy_type, base_count in self.PROPOSAL_COUNTS.items():
            base = StrategyActionCatalogEntry.objects.filter(
                strategy_type=strategy_type
            ).exclude(code__endswith="RESCIND")
            self.assertEqual(
                base.count(),
                base_count,
                f"Proposal list count mismatch for {strategy_type}",
            )

    def test_rescind_templates_on_agreement_strategies(self):
        for strategy_type in ("Compromise", "Restructuring"):
            self.assertTrue(
                StrategyActionCatalogEntry.objects.filter(
                    strategy_type=strategy_type, code__endswith="RESCIND"
                ).exists(),
                f"Missing rescind template for {strategy_type}",
            )

    def test_approval_gated_classification_follows_d3(self):
        gated = set(
            StrategyActionCatalogEntry.objects.filter(requires_approval=True)
            .exclude(code__endswith="RESCIND")
            .values_list("strategy_type", "code")
        )
        expected_gated = {
            ("Intensive Collection", "IC-AGENCY"),
            ("Restructuring", "RS-EXTENSION"),
            ("Restructuring", "RS-AMORTIZATION"),
            ("Restructuring", "RS-FREQUENCY"),
            ("Restructuring", "RS-MORATORIUM"),
            ("Restructuring", "RS-REVISION"),
            ("Restructuring", "RS-SECURITY"),
            ("Restructuring", "RS-CONSOLIDATION"),
            ("Compromise", "CP-FULL"),
            ("Compromise", "CP-PARTIAL-CONDONATION"),
            ("Compromise", "CP-INSTALLMENT"),
            ("Compromise", "CP-DISCOUNTED"),
            ("Compromise", "CP-ASSET-PROCEEDS"),
            ("Foreclosure", "CR-EXTRAJUDICIAL"),
            ("Foreclosure", "CR-JUDICIAL"),
            ("Foreclosure", "CR-REPOSSESSION"),
            ("Foreclosure", "CR-DISPOSAL"),
            ("Legal Action", "LA-COUNSEL"),
            ("Legal Action", "LA-FILING"),
            ("Legal Action", "LA-FORECLOSURE-PROCEEDINGS"),
            ("Legal Action", "LA-JUDGMENT-ENFORCEMENT"),
            ("Legal Action", "LA-ASSET-EXECUTION"),
            ("Write-Off", "WO-APPROVAL"),
            ("Write-Off", "WO-AGENCY"),
        }
        self.assertEqual(gated, expected_gated)
        self.assertFalse(
            StrategyActionCatalogEntry.objects.get(code="IC-CALL").requires_approval
        )
        self.assertFalse(
            StrategyActionCatalogEntry.objects.get(code="CR-SURRENDER").requires_approval
        )


class AdminRegistrationTest(TestCase):
    """Task 2.2: every new model is browsable in admin with no broken URLs."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", email="a@a.com", password="pass"
        )
        self.account = make_account()
        self.strategy = make_strategy(self.account)

    def test_admin_registers_all_framework_models(self):
        from django.contrib import admin as django_admin

        from account_master.admin import (
            CollateralAdmin,
            GuarantorAdmin,
            StrategyActionAdmin,
            StrategyActionCatalogEntryAdmin,
            StrategyApprovalAdmin,
            StrategyAssessmentAdmin,
        )

        for model, admin_class in [
            (Guarantor, GuarantorAdmin),
            (Collateral, CollateralAdmin),
            (StrategyAssessment, StrategyAssessmentAdmin),
            (StrategyActionCatalogEntry, StrategyActionCatalogEntryAdmin),
            (StrategyAction, StrategyActionAdmin),
            (StrategyApproval, StrategyApprovalAdmin),
        ]:
            self.assertIsInstance(
                django_admin.site._registry[model], admin_class, model.__name__
            )

    def test_admin_pages_are_browsable(self):
        self.client.force_login(self.superuser)
        for model in [
            Guarantor,
            Collateral,
            StrategyAssessment,
            StrategyActionCatalogEntry,
            StrategyAction,
            StrategyApproval,
        ]:
            url = reverse(f"admin:account_master_{model._meta.model_name}_changelist")
            self.assertEqual(self.client.get(url).status_code, 200, url)


# ===========================================================================
# 3. Strategy service
# ===========================================================================


class RecommendationCreationServiceTest(TestCase):
    """Task 3.1: recommendation activates the strategy; one ACTIVE per account."""

    def setUp(self):
        self.account = make_account()
        self.officer, _, _ = make_users()

    def test_recommendation_creates_active_strategy_with_assessment(self):
        strategy = strategy_service.create_strategy_recommendation(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(),
        )
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)
        assessment = StrategyAssessment.objects.get(strategy=strategy)
        self.assertEqual(assessment.as_of_date, _today())
        self.assertEqual(assessment.officer_rationale, base_assessment()["officer_rationale"])

    def test_recommendation_requires_officer_rationale(self):
        with self.assertRaises(ValidationError):
            strategy_service.create_strategy_recommendation(
                account=self.account,
                strategy_type="Intensive Collection",
                strategy_start_date=_today(),
                officer=self.officer,
                assessment=base_assessment(officer_rationale=""),
            )

    def test_competing_active_strategy_is_superseded(self):
        first = strategy_service.create_strategy_recommendation(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(),
        )
        second = strategy_service.create_strategy_recommendation(
            account=self.account,
            strategy_type="Restructuring",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(),
        )
        first.refresh_from_db()
        self.assertEqual(first.strategy_status, RemedialStrategy.StrategyStatus.CANCELLED)
        self.assertEqual(second.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)
        active_count = self.account.remedial_strategies.filter(
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE
        ).count()
        self.assertEqual(active_count, 1)

    def test_snapshot_copies_delinquency_and_exposure_values(self):
        from account_master.models import DelinquencyStatus, Exposure

        Exposure.objects.create(
            account=self.account,
            as_of_date=_today(),
            snapshot_type="EVENT",
            principal_outstanding=Decimal("8000.00"),
            accrued_interest=Decimal("500.00"),
            accrued_penalty=Decimal("200.00"),
            days_past_due=45,
        )
        DelinquencyStatus.objects.create(
            account=self.account,
            as_of_date=_today(),
            snapshot_type="EVENT",
            days_past_due=45,
            aging_bucket="31-60",
            classification="SS",
        )
        strategy = strategy_service.create_strategy_recommendation(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(),
        )
        assessment = strategy.assessment
        self.assertEqual(assessment.days_past_due, 45)
        self.assertEqual(assessment.aging_bucket, "31-60")
        self.assertEqual(assessment.classification, "SS")
        self.assertEqual(assessment.outstanding_exposure, Decimal("8700.00"))


class ActionSelectionExecutionServiceTest(TestCase):
    """Task 3.2: gated blocked until approved; non-gated executed directly."""

    def setUp(self):
        self.account = make_account()
        self.officer, _, _ = make_users()
        self.strategy = make_strategy(self.account)

    def test_selecting_non_gated_action_executes_directly(self):
        entry = StrategyActionCatalogEntry.objects.get(code="IC-CALL")
        action = strategy_service.select_action(
            strategy=self.strategy,
            catalog_entry=entry,
            assignee="Agent A",
            officer=self.officer,
        )
        self.assertEqual(action.status, StrategyAction.ActionStatus.SELECTED)
        strategy_service.execute_action(
            action=action, outcome="Borrower contacted", officer=self.officer
        )
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.EXECUTED)
        self.assertEqual(action.outcome, "Borrower contacted")
        self.assertEqual(action.assignee, "Agent A")

    def test_gated_action_cannot_be_executed_before_approval(self):
        entry = StrategyActionCatalogEntry.objects.get(code="IC-AGENCY")
        action = strategy_service.select_action(
            strategy=self.strategy, catalog_entry=entry, officer=self.officer
        )
        self.assertEqual(action.status, StrategyAction.ActionStatus.PENDING_APPROVAL)
        with self.assertRaises(ValidationError):
            strategy_service.execute_action(
                action=action, outcome="Premature", officer=self.officer
            )
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.PENDING_APPROVAL)

    def test_only_own_catalog_actions_can_be_selected(self):
        foreign = StrategyActionCatalogEntry.objects.get(code="CP-FULL")
        with self.assertRaises(ValidationError):
            strategy_service.select_action(
                strategy=self.strategy, catalog_entry=foreign, officer=self.officer
            )


class ApprovalWorkflowServiceTest(TestCase):
    """Task 3.3: manager is the sole approver; board reads without deciding."""

    def setUp(self):
        self.account = make_account()
        self.officer, self.manager, self.board = make_users()
        self.strategy = make_strategy(self.account)
        self.entry = StrategyActionCatalogEntry.objects.get(code="IC-AGENCY")
        self.action = strategy_service.select_action(
            strategy=self.strategy, catalog_entry=self.entry, officer=self.officer
        )

    def test_non_manager_approval_attempt_is_rejected(self):
        with self.assertRaises(ValidationError):
            strategy_service.approve_action(action=self.action, approver=self.officer)
        with self.assertRaises(ValidationError):
            strategy_service.approve_action(action=self.action, approver=self.board)
        with self.assertRaises(ValidationError):
            strategy_service.reject_action(action=self.action, approver=self.board)
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.PENDING_APPROVAL)

    def test_manager_approval_releases_action_and_records_conditions(self):
        strategy_service.approve_action(
            action=self.action,
            approver=self.manager,
            comments="Approved",
            conditions="Subject to 20% downpayment within 10 days",
        )
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.APPROVED)
        approval = self.action.approvals.get()
        self.assertEqual(approval.approver, self.manager)
        self.assertEqual(approval.decision, "APPROVED")
        self.assertEqual(approval.conditions, "Subject to 20% downpayment within 10 days")
        strategy_service.execute_action(
            action=self.action, outcome="Booked", officer=self.officer
        )
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.EXECUTED)

    def test_manager_rejection_keeps_action_unexecuted(self):
        strategy_service.reject_action(
            action=self.action, approver=self.manager, comments="Not in policy"
        )
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.REJECTED)
        approval = self.action.approvals.get()
        self.assertEqual(approval.decision, "REJECTED")
        self.assertFalse(self.action.is_released_for_execution)

    def test_board_member_reads_without_deciding(self):
        self.assertIn(self.action, list(strategy_service.list_pending_approvals()))
        with self.assertRaises(ValidationError):
            strategy_service.approve_action(action=self.action, approver=self.board)


class FailureAndRescindServiceTest(TestCase):
    """Task 3.4: officer-declared failure and the agreement rescind flow."""

    def setUp(self):
        self.account = make_account()
        self.officer, self.manager, _ = make_users()
        self.strategy = make_strategy(self.account, strategy_type="Compromise")
        self.agreement = CompromiseAgreement.objects.create(
            strategy=self.strategy,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("5000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="ACTIVE",
            created_by=self.officer,
            updated_by=self.officer,
        )

    def test_unmet_conditions_declaration_marks_agreement_unsuccessful_and_opens_rescind(self):
        strategy_service.declare_failure(
            strategy=self.strategy,
            officer=self.officer,
            unmet_conditions_note="Borrower failed the 20% downpayment requirement",
        )
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.status, "UNSUCCESSFUL")
        self.strategy.refresh_from_db()
        self.assertEqual(self.strategy.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)
        rescind = self.strategy.actions.filter(catalog_entry__code__endswith="RESCIND").first()
        self.assertIsNotNone(rescind)
        self.assertEqual(rescind.status, StrategyAction.ActionStatus.PENDING_APPROVAL)
        self.assertTrue(rescind.requires_approval)

    def test_approved_rescind_closes_strategy_and_rescinds_agreement(self):
        strategy_service.declare_failure(strategy=self.strategy, officer=self.officer)
        rescind = self.strategy.actions.filter(catalog_entry__code__endswith="RESCIND").first()
        strategy_service.approve_action(action=rescind, approver=self.manager)
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.status, "RESCINDED")
        self.strategy.refresh_from_db()
        self.assertEqual(self.strategy.strategy_status, RemedialStrategy.StrategyStatus.CANCELLED)

    def test_rejected_rescind_keeps_strategy_active(self):
        strategy_service.declare_failure(strategy=self.strategy, officer=self.officer)
        rescind = self.strategy.actions.filter(catalog_entry__code__endswith="RESCIND").first()
        strategy_service.reject_action(action=rescind, approver=self.manager)
        rescind.refresh_from_db()
        self.assertEqual(rescind.status, StrategyAction.ActionStatus.REJECTED)
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.status, "UNSUCCESSFUL")
        self.strategy.refresh_from_db()
        self.assertEqual(self.strategy.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)

    def test_non_agreement_strategy_failure_cancels_directly(self):
        strategy = make_strategy(self.account, strategy_type="Intensive Collection")
        strategy_service.declare_failure(
            strategy=strategy, officer=self.officer, outcome="Borrower unreachable"
        )
        strategy.refresh_from_db()
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.CANCELLED)
        self.assertEqual(strategy.strategy_outcome, "Borrower unreachable")
        self.assertEqual(strategy.actions.count(), 0)


class ApprovalSideEffectServiceTest(TestCase):
    """Task 3.5: write-off books the account; settlement activates the agreement."""

    def setUp(self):
        self.account = make_account(status="NPL")
        self.officer, self.manager, _ = make_users()

    def test_approved_write_off_sets_account_status(self):
        strategy = make_strategy(self.account, strategy_type="Write-Off")
        entry = StrategyActionCatalogEntry.objects.get(code="WO-APPROVAL")
        action = strategy_service.select_action(
            strategy=strategy, catalog_entry=entry, officer=self.officer
        )
        strategy_service.approve_action(action=action, approver=self.manager)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "WRITEOFF")
        strategy.refresh_from_db()
        self.assertEqual(strategy.strategy_outcome, "Write-off booked.")

    def test_approved_settlement_activates_agreement(self):
        strategy = make_strategy(self.account, strategy_type="Compromise")
        agreement = CompromiseAgreement.objects.create(
            strategy=strategy,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("5000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="PENDING_APPROVAL",
            created_by=self.officer,
            updated_by=self.officer,
        )
        entry = StrategyActionCatalogEntry.objects.get(code="CP-FULL")
        action = strategy_service.select_action(
            strategy=strategy, catalog_entry=entry, officer=self.officer
        )
        strategy_service.approve_action(
            action=action,
            approver=self.manager,
            conditions="Subject to 20% downpayment within 10 days",
        )
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, "ACTIVE")


# ===========================================================================
# 4. Lifecycle gates & escalation
# ===========================================================================


class EntryGateServiceTest(TestCase):
    """Task 4.1: Legal Action / Foreclosure entry gates."""

    def setUp(self):
        self.officer, _, _ = make_users()
        self.account = make_account(loan_security="SECURED")

    def _terminal_ladder(self):
        from account_master.models import EscalationStage

        state = escalation_service.start_escalation(self.account)[0]
        terminal = state.current_stage
        while not terminal.is_terminal:
            terminal = (
                EscalationStage.objects.filter(stage_no__gt=terminal.stage_no)
                .order_by("stage_no")
                .first()
            )
        escalation_service.close_escalation(
            self.account, EscalationState.CloseReason.TERMINAL
        )

    def test_ungated_legal_action_is_blocked(self):
        with self.assertRaises(ValidationError):
            strategy_service.create_strategy_recommendation(
                account=self.account,
                strategy_type="Legal Action",
                strategy_start_date=_today(),
                officer=self.officer,
                assessment=base_assessment(),
            )

    def test_approved_litigation_entry_satisfies_legal_action_gate(self):
        manager = User.objects.create_user(
            username="lit-mgr1", password="pass", role=User.Role.MANAGER
        )
        entry = litigation_service.raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Account already in legal proceedings.",
            officer=self.officer,
        )
        litigation_service.approve_litigation_entry(entry, approver=manager)
        strategy = strategy_service.create_strategy_recommendation(
            account=self.account,
            strategy_type="Legal Action",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(),
        )
        self.assertEqual(strategy.strategy_type, "Legal Action")

    def test_pending_litigation_entry_does_not_satisfy_gate(self):
        litigation_service.raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Account already in legal proceedings.",
            officer=self.officer,
        )
        with self.assertRaises(ValidationError):
            strategy_service.create_strategy_recommendation(
                account=self.account,
                strategy_type="Legal Action",
                strategy_start_date=_today(),
                officer=self.officer,
                assessment=base_assessment(),
            )

    def test_rejected_litigation_entry_does_not_satisfy_gate(self):
        manager = User.objects.create_user(
            username="lit-mgr2", password="pass", role=User.Role.MANAGER
        )
        entry = litigation_service.raise_litigation_entry(
            account=self.account,
            strategy_type="Legal Action",
            start_date=_today(),
            rationale="Account already in legal proceedings.",
            officer=self.officer,
        )
        litigation_service.reject_litigation_entry(entry, approver=manager)
        with self.assertRaises(ValidationError):
            strategy_service.create_strategy_recommendation(
                account=self.account,
                strategy_type="Legal Action",
                strategy_start_date=_today(),
                officer=self.officer,
                assessment=base_assessment(),
            )

    def test_ladder_terminal_satisfies_legal_action_gate(self):
        self._terminal_ladder()
        strategy = strategy_service.create_strategy_recommendation(
            account=self.account,
            strategy_type="Legal Action",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(),
        )
        self.assertEqual(strategy.strategy_type, "Legal Action")
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)

    def test_foreclosure_gate_requires_secured(self):
        self._terminal_ladder()
        self.account.loan_security = "UNSECURED"
        self.account.save()
        with self.assertRaises(ValidationError):
            strategy_service.create_strategy_recommendation(
                account=self.account,
                strategy_type="Foreclosure",
                strategy_start_date=_today(),
                officer=self.officer,
                assessment=base_assessment(),
            )

    def test_approved_rescind_satisfies_gate_without_open_ladder(self):
        strategy = make_strategy(self.account, strategy_type="Compromise")
        CompromiseAgreement.objects.create(
            strategy=strategy,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("5000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="ACTIVE",
        )
        manager = User.objects.create_user(
            username="mgr2", password="pass", role=User.Role.MANAGER
        )
        strategy_service.declare_failure(strategy=strategy, officer=self.officer)
        rescind = strategy.actions.filter(catalog_entry__code__endswith="RESCIND").first()
        strategy_service.approve_action(action=rescind, approver=manager)
        strategy.refresh_from_db()
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.CANCELLED)
        legal = strategy_service.create_strategy_recommendation(
            account=self.account,
            strategy_type="Legal Action",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(),
        )
        self.assertEqual(legal.strategy_type, "Legal Action")


class EscalationLadderRescindTest(TestCase):
    """Task 4.2: a rescinded arrangement keeps the ladder closed."""

    def setUp(self):
        self.officer, _, _ = make_users()
        self.account = make_account(status="NPL")

    def test_rescinded_arrangement_keeps_ladder_closed(self):
        state, created = escalation_service.start_escalation(self.account)
        self.assertTrue(created)
        escalation_service.close_escalation(
            self.account, EscalationState.CloseReason.ARRANGEMENT
        )
        strategy = make_strategy(self.account, strategy_type="Compromise")
        CompromiseAgreement.objects.create(
            strategy=strategy,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("5000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="RESCINDED",
        )
        state, created = escalation_service.start_escalation(self.account)
        self.assertFalse(created)
        self.assertIsNone(state)
        self.assertIsNone(escalation_service.get_open_state(self.account))
        escalation_service.sync_escalation_on_snapshot(
            self.account, derived_status="NPL"
        )
        self.assertIsNone(escalation_service.get_open_state(self.account))

    def test_ladder_reopens_when_arrangement_still_in_effect(self):
        state, created = escalation_service.start_escalation(self.account)
        self.assertTrue(created)
        escalation_service.close_escalation(
            self.account, EscalationState.CloseReason.ARRANGEMENT
        )
        state, created = escalation_service.start_escalation(self.account)
        self.assertTrue(created)
        self.assertIsNotNone(state)


class CompletionTransitionServiceTest(TestCase):
    """Task 4.3: strategy completes only on its type's completion condition."""

    def setUp(self):
        self.officer, _, _ = make_users()
        self.account = make_account(status="NPL")

    def _installment(self, agreement, paid=False):
        from compromise_agreement.models import CompromiseInstallment

        return CompromiseInstallment.objects.create(
            compromise_agreement=agreement,
            installment_number=1,
            due_date=_today(),
            amount_due=Decimal("1000.00"),
            amount_paid=Decimal("1000.00") if paid else Decimal("0.00"),
            status="PAID" if paid else "UNPAID",
        )

    def test_intensive_collection_completes_on_cure(self):
        strategy = make_strategy(self.account, strategy_type="Intensive Collection")
        self.assertFalse(strategy_service.is_completion_condition_met(strategy))
        self.account.status = "PERFORMING"
        self.account.save()
        self.assertTrue(strategy_service.is_completion_condition_met(strategy))
        strategy_service.complete_strategy(strategy=strategy, user=self.officer)
        strategy.refresh_from_db()
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.COMPLETED)

    def test_compromise_completes_when_fully_paid(self):
        strategy = make_strategy(self.account, strategy_type="Compromise")
        agreement = CompromiseAgreement.objects.create(
            strategy=strategy,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("5000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="ACTIVE",
        )
        installment = self._installment(agreement, paid=False)
        self.assertFalse(strategy_service.is_completion_condition_met(strategy))
        installment.status = "PAID"
        installment.amount_paid = Decimal("1000.00")
        installment.save()
        self.assertTrue(strategy_service.is_completion_condition_met(strategy))
        strategy_service.complete_strategy(strategy=strategy, user=self.officer)
        strategy.refresh_from_db()
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.COMPLETED)

    def test_write_off_completes_when_booked(self):
        strategy = make_strategy(self.account, strategy_type="Write-Off")
        self.assertFalse(strategy_service.is_completion_condition_met(strategy))
        self.account.status = "WRITEOFF"
        self.account.save()
        self.assertTrue(strategy_service.is_completion_condition_met(strategy))

    def test_wrong_condition_is_blocked(self):
        strategy = make_strategy(self.account, strategy_type="Intensive Collection")
        with self.assertRaises(ValidationError):
            strategy_service.complete_strategy(strategy=strategy, user=self.officer)


class EscalationFollowsExitServiceTest(TestCase):
    """Task 4.4: next recommendation only after exit; fresh snapshot recorded."""

    def setUp(self):
        self.officer, _, _ = make_users()
        self.account = make_account()

    def test_recommendation_blocked_while_strategy_active(self):
        make_strategy(self.account, strategy_type="Intensive Collection")
        with self.assertRaises(ValidationError):
            strategy_service.recommend_next_strategy(
                account=self.account,
                strategy_type="Restructuring",
                strategy_start_date=_today(),
                officer=self.officer,
                assessment=base_assessment(),
            )

    def test_escalation_follows_exit_with_fresh_snapshot(self):
        first = make_strategy(self.account, strategy_type="Intensive Collection")
        make_assessment(first, self.officer)
        first.strategy_status = RemedialStrategy.StrategyStatus.COMPLETED
        first.save()
        second = strategy_service.recommend_next_strategy(
            account=self.account,
            strategy_type="Restructuring",
            strategy_start_date=_today(),
            officer=self.officer,
            assessment=base_assessment(officer_rationale="Escalated to restructuring"),
        )
        self.assertEqual(second.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)
        fresh = StrategyAssessment.objects.get(strategy=second)
        self.assertEqual(fresh.officer_rationale, "Escalated to restructuring")
        prior = StrategyAssessment.objects.get(strategy=first)
        self.assertEqual(prior.officer_rationale, first.assessment.officer_rationale)
        self.assertEqual(
            StrategyAssessment.objects.filter(strategy__account=self.account).count(), 2
        )


# ===========================================================================
# 5. UI & permissions
# ===========================================================================


class AssessmentCaptureViewTest(TestCase):
    """Task 5.1: strategy creation flow captures the assessment."""

    def setUp(self):
        self.client = None
        from django.test import Client

        self.client = Client()
        self.officer, _, _ = make_users()
        self.account = make_account()
        self.url = reverse("create_remedial_strategy", args=[self.account.loan_id])

    def _post(self, **overrides):
        data = {
            "strategy_type": "Intensive Collection",
            "strategy_start_date": "2023-07-01",
            "as_of_date": "2023-07-01",
            "officer_rationale": "Cash-flow collapse after business closure",
            "financial_condition": "STRONG",
            "financial_condition_note": "Other income streams",
            "willingness_to_pay": "HIGH",
            "recovery_outlook": "MEDIUM",
            "expected_recovery": "1500.00",
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_create_flow_requires_assessment_with_rationale(self):
        self.client.force_login(self.officer)
        response = self._post(officer_rationale="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.account.remedial_strategies.exists(),
            "A recommendation without rationale must not create a strategy.",
        )

    def test_create_flow_records_snapshot_as_of_recommendation_date(self):
        self.client.force_login(self.officer)
        response = self._post()
        self.assertRedirects(
            response, reverse("account_detail", args=[self.account.loan_id])
        )
        strategy = self.account.remedial_strategies.get()
        self.assertEqual(strategy.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)
        assessment = StrategyAssessment.objects.get(strategy=strategy)
        self.assertEqual(assessment.as_of_date, datetime.date(2023, 7, 1))
        self.assertEqual(assessment.officer_rationale, "Cash-flow collapse after business closure")
        self.assertEqual(assessment.financial_condition, "STRONG")
        self.assertEqual(assessment.willingness_to_pay, "HIGH")
        self.assertEqual(assessment.recovery_outlook, "MEDIUM")

    def test_ungated_legal_action_renders_litigation_entry_message(self):
        self.client.force_login(self.officer)
        response = self._post(strategy_type="Legal Action")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.account.remedial_strategies.filter(strategy_type="Legal Action").exists()
        )
        body = response.content.decode()
        self.assertIn("litigation entry", body.lower())


class StrategyDetailViewTest(TestCase):
    """Task 5.2: action catalog menu, tracked action statuses, approval state."""

    def setUp(self):
        from django.test import Client

        self.client = Client()
        self.officer, _, _ = make_users()
        self.account = make_account()
        strategy = make_strategy(self.account, strategy_type="Intensive Collection")
        make_assessment(strategy, self.officer)
        self.strategy = strategy
        self.url = reverse(
            "remedial_strategy_detail",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )

    def test_detail_shows_catalog_and_assessment(self):
        self.client.force_login(self.officer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("catalog", response.context)
        self.assertIn("actions", response.context)
        self.assertIsNotNone(response.context["assessment"])
        self.assertIn("Action Catalog", response.content.decode())

    def test_officer_selects_and_executes_non_gated_action(self):
        self.client.force_login(self.officer)
        entry = StrategyActionCatalogEntry.objects.get(code="IC-CALL")
        response = self.client.post(
            self.url,
            {
                "action": "select",
                "catalog_entry_id": entry.catalog_entry_id,
                "assignee": "Agent A",
            },
        )
        self.assertRedirects(response, self.url)
        action = self.strategy.actions.get(catalog_entry=entry)
        self.assertEqual(action.status, StrategyAction.ActionStatus.SELECTED)
        response = self.client.post(
            self.url,
            {"action": "execute", "action_id": action.action_id,
             "outcome": "Contacted borrower"},
        )
        self.assertRedirects(response, self.url)
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.EXECUTED)

    def test_gated_selection_sits_pending_approval(self):
        self.client.force_login(self.officer)
        entry = StrategyActionCatalogEntry.objects.get(code="IC-AGENCY")
        self.client.post(
            self.url,
            {"action": "select", "catalog_entry_id": entry.catalog_entry_id},
        )
        action = self.strategy.actions.get(catalog_entry=entry)
        self.assertEqual(action.status, StrategyAction.ActionStatus.PENDING_APPROVAL)
        # Attempting execution via the view is refused (redirect + still pending)
        response = self.client.post(
            self.url,
            {"action": "execute", "action_id": action.action_id,
             "outcome": "Premature"},
        )
        self.assertRedirects(response, self.url)
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.PENDING_APPROVAL)


class ApprovalQueueViewTest(TestCase):
    """Task 5.3: manager approval queue end-to-end walkthrough."""

    def setUp(self):
        from django.test import Client

        self.client = Client()
        self.officer, self.manager, _ = make_users()
        self.account = make_account()
        self.strategy = make_strategy(self.account, strategy_type="Intensive Collection")
        entry = StrategyActionCatalogEntry.objects.get(code="IC-AGENCY")
        self.action = strategy_service.select_action(
            strategy=self.strategy, catalog_entry=entry, officer=self.officer
        )
        self.queue_url = reverse("approval_queue")

    def test_manager_walkthrough_approve_with_conditions(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.queue_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.action, list(response.context["pending_actions"]))
        response = self.client.post(
            self.queue_url,
            {
                "action_id": self.action.action_id,
                "decision": "approve",
                "conditions": "Subject to 20% downpayment within 10 days",
            },
        )
        self.assertRedirects(response, self.queue_url)
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.APPROVED)
        approval = self.action.approvals.get()
        self.assertEqual(approval.conditions, "Subject to 20% downpayment within 10 days")
        self.assertEqual(approval.approver, self.manager)

    def test_manager_walkthrough_reject(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            self.queue_url,
            {"action_id": self.action.action_id, "decision": "reject"},
        )
        self.assertRedirects(response, self.queue_url)
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, StrategyAction.ActionStatus.REJECTED)


class PermissionGatingViewTest(TestCase):
    """Task 5.4: board reads strategy pages; non-managers cannot decide."""

    def setUp(self):
        from django.test import Client

        self.client = Client()
        self.officer, self.manager, self.board = make_users()
        self.account = make_account()
        self.strategy = make_strategy(self.account, strategy_type="Intensive Collection")
        make_assessment(self.strategy, self.officer)
        self.detail_url = reverse(
            "remedial_strategy_detail",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )
        self.queue_url = reverse("approval_queue")

    def test_board_member_reads_strategy_page(self):
        self.client.force_login(self.board)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("intensive", response.content.decode().lower())

    def test_board_member_cannot_mutate_strategy(self):
        self.client.force_login(self.board)
        entry = StrategyActionCatalogEntry.objects.get(code="IC-CALL")
        response = self.client.post(
            self.detail_url,
            {"action": "select", "catalog_entry_id": entry.catalog_entry_id},
        )
        self.assertRedirects(response, self.detail_url)
        self.assertEqual(self.strategy.actions.count(), 0)

    def test_non_managers_cannot_access_approval_queue(self):
        self.client.force_login(self.board)
        self.assertEqual(self.client.get(self.queue_url).status_code, 403)
        self.client.force_login(self.officer)
        self.assertEqual(self.client.get(self.queue_url).status_code, 403)

    def test_manager_can_access_approval_queue(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(self.queue_url).status_code, 200)


class StrategyTypeLabelTest(TestCase):
    """Task 5.5: display labels refined; stored values unchanged."""

    def test_display_labels_and_stored_values(self):
        expected = {
            "Intensive Collection": "Intensive Collection",
            "Restructuring": "Loan Restructuring / Rehabilitation",
            "Compromise": "Compromise Settlement",
            "Foreclosure": "Collateral Recovery / Foreclosure",
            "Legal Action": "Legal Action",
            "Write-Off": "Write-Off / Post-Write-off Recovery",
        }
        for stored, label in expected.items():
            strategy = make_strategy(make_account(loan_id=f"L-{stored[:3]}"), strategy_type=stored)
            self.assertEqual(strategy.strategy_type, stored)
            self.assertEqual(strategy.get_strategy_type_display(), label)

    def test_label_renders_on_detail_page(self):
        from django.test import Client

        client = Client()
        officer, _, _ = make_users()
        account = make_account()
        strategy = make_strategy(account, strategy_type="Restructuring")
        make_assessment(strategy, officer)
        client.force_login(officer)
        response = client.get(
            reverse(
                "remedial_strategy_detail",
                args=[account.loan_id, strategy.strategy_id],
            )
        )
        self.assertContains(response, "Loan Restructuring / Rehabilitation")


# ===========================================================================
# 6. End-to-end integration
# ===========================================================================


class EndToEndIntegrationTest(TestCase):
    """Task 6.1: full flow across all four spec deltas."""

    def test_full_recommend_approve_rescind_escalate_flow(self):
        officer, manager, _ = make_users()
        account = make_account(loan_id="E2E-001", loan_security="SECURED", status="NPL")

        # 1. Recommend an active strategy with an assessment snapshot
        compromise = strategy_service.create_strategy_recommendation(
            account=account,
            strategy_type="Compromise",
            strategy_start_date=_today(),
            officer=officer,
            assessment=base_assessment(
                as_of_date=_today(),
                officer_rationale="Compromise recommended to recover principal",
                willingness_to_pay="MEDIUM",
            ),
        )
        self.assertEqual(
            compromise.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE
        )
        first_assessment = StrategyAssessment.objects.get(strategy=compromise)
        self.assertEqual(first_assessment.as_of_date, _today())

        # 2. Agreement held non-ACTIVE until the settlement is approved (D7)
        agreement = CompromiseAgreement.objects.create(
            strategy=compromise,
            account=account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("5000.00"),
            approval_level="MANAGER",
            approval_date=_today(),
            status="PENDING_APPROVAL",
            installment_flag=True,
            number_of_installments=5,
            payment_frequency="MONTHLY",
            first_payment_date=_today(),
            created_by=officer,
            updated_by=officer,
        )

        # 3. Select a gated action; it sits pending approval
        settlement = strategy_service.select_action(
            strategy=compromise,
            catalog_entry=StrategyActionCatalogEntry.objects.get(code="CP-FULL"),
            officer=officer,
        )
        self.assertEqual(settlement.status, StrategyAction.ActionStatus.PENDING_APPROVAL)

        # 4. Manager approves with conditions; agreement activates
        strategy_service.approve_action(
            action=settlement,
            approver=manager,
            conditions="Subject to 20% downpayment within 10 days",
        )
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, "ACTIVE")
        # Approved arrangement closes the escalation ladder
        escalation_service.start_escalation(account)
        escalation_service.sync_escalation_on_snapshot(account, derived_status="NPL")
        open_state = escalation_service.get_open_state(account)
        self.assertIsNone(open_state)

        # 5. Officer executes the approved action
        strategy_service.execute_action(
            action=settlement, outcome="Downpayment collected", officer=officer
        )
        settlement.refresh_from_db()
        self.assertEqual(settlement.status, StrategyAction.ActionStatus.EXECUTED)

        # 6. Officer declares failure because conditions were not met
        strategy_service.declare_failure(
            strategy=compromise,
            officer=officer,
            unmet_conditions_note="Remaining payments defaulted after the first installment",
        )
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, "UNSUCCESSFUL")
        rescind = compromise.actions.filter(
            catalog_entry__code__endswith="RESCIND"
        ).first()
        self.assertIsNotNone(rescind)
        self.assertEqual(rescind.status, StrategyAction.ActionStatus.PENDING_APPROVAL)

        # 7. Manager approves the rescind: agreement RESCINDED, strategy CANCELLED
        strategy_service.approve_action(action=rescind, approver=manager)
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, "RESCINDED")
        compromise.refresh_from_db()
        self.assertEqual(compromise.strategy_status, RemedialStrategy.StrategyStatus.CANCELLED)

        # 8. Rescinded arrangement keeps the ladder closed (spec delta 4)
        state, created = escalation_service.start_escalation(account)
        self.assertFalse(created)
        self.assertIsNone(state)

        # 9. Escalate: next strategy with a fresh assessment; prior snapshot intact
        legal = strategy_service.recommend_next_strategy(
            account=account,
            strategy_type="Legal Action",
            strategy_start_date=_today(),
            officer=officer,
            assessment=base_assessment(
                as_of_date=_today(),
                officer_rationale="Escalated to legal action after failed compromise",
                recovery_outlook="LOW",
            ),
        )
        self.assertEqual(legal.strategy_type, "Legal Action")
        self.assertEqual(legal.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE)
        fresh = StrategyAssessment.objects.get(strategy=legal)
        self.assertEqual(fresh.officer_rationale, "Escalated to legal action after failed compromise")
        first_assessment.refresh_from_db()
        self.assertEqual(first_assessment.officer_rationale, "Compromise recommended to recover principal")
        self.assertEqual(
            StrategyAssessment.objects.filter(strategy__account=account).count(), 2
        )


class ActionEditingTests(TestCase):
    """Editing planning fields, outcome lock, and skip-with-reason for actions."""

    def setUp(self):
        self.officer, self.manager, _board = make_users()
        self.account = make_account(loan_id="L-EDIT")
        self.strategy = make_strategy(self.account)
        self.entry = StrategyActionCatalogEntry.objects.create(
            strategy_type="Intensive Collection",
            code="IC-EDIT",
            name="Call",
            ordering=1,
            requires_approval=False,
        )
        self.gated_entry = StrategyActionCatalogEntry.objects.create(
            strategy_type="Intensive Collection",
            code="IC-EDIT-GATED",
            name="Commitment",
            ordering=2,
            requires_approval=True,
        )

    def _action(self, status, catalog=None):
        return StrategyAction.objects.create(
            catalog_entry=catalog or self.entry,
            strategy=self.strategy,
            status=status,
            created_by=self.officer,
            updated_by=self.officer,
        )

    def test_edit_planning_accepted_in_non_terminal_statuses(self):
        for status in (
            StrategyAction.ActionStatus.SELECTED,
            StrategyAction.ActionStatus.PENDING_APPROVAL,
            StrategyAction.ActionStatus.APPROVED,
        ):
            with self.subTest(status=status):
                action = self._action(status)
                strategy_service.update_action_planning(
                    action=action,
                    assignee="Officer B",
                    due_date="2026-12-01",
                    officer=self.officer,
                )
                action.refresh_from_db()
                self.assertEqual(action.assignee, "Officer B")
                self.assertEqual(action.due_date, datetime.date(2026, 12, 1))

    def test_edit_planning_rejected_in_terminal_statuses(self):
        for status in (
            StrategyAction.ActionStatus.EXECUTED,
            StrategyAction.ActionStatus.SKIPPED,
            StrategyAction.ActionStatus.REJECTED,
        ):
            with self.subTest(status=status):
                action = self._action(status)
                with self.assertRaises(ValidationError):
                    strategy_service.update_action_planning(
                        action=action,
                        assignee="Changed",
                        due_date=None,
                        officer=self.officer,
                    )
                action.refresh_from_db()
                self.assertEqual(action.assignee, "")

    def test_skip_non_gated_selected_action(self):
        action = self._action(StrategyAction.ActionStatus.SELECTED)
        strategy_service.skip_action(
            action=action,
            outcome="Resolved via other channel",
            officer=self.officer,
        )
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.SKIPPED)
        self.assertEqual(action.outcome, "Resolved via other channel")

    def test_skip_approved_gated_action(self):
        action = self._action(
            StrategyAction.ActionStatus.APPROVED, catalog=self.gated_entry
        )
        strategy_service.skip_action(
            action=action,
            outcome="Manager redeployed staff",
            officer=self.officer,
        )
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.SKIPPED)

    def test_skip_rejected_in_ineligible_statuses(self):
        cases = [
            (StrategyAction.ActionStatus.PENDING_APPROVAL, self.gated_entry),
            (StrategyAction.ActionStatus.REJECTED, self.gated_entry),
            (StrategyAction.ActionStatus.EXECUTED, self.entry),
            (StrategyAction.ActionStatus.SKIPPED, self.entry),
        ]
        for status, catalog in cases:
            with self.subTest(status=status):
                action = self._action(status, catalog=catalog)
                with self.assertRaises(ValidationError):
                    strategy_service.skip_action(
                        action=action, outcome="x", officer=self.officer
                    )

    def test_update_path_never_writes_outcome(self):
        action = self._action(StrategyAction.ActionStatus.EXECUTED)
        action.outcome = "Already completed"
        action.save(update_fields=["outcome"])
        with self.assertRaises(ValidationError):
            strategy_service.update_action_planning(
                action=action, assignee="Y", officer=self.officer
            )
        action.refresh_from_db()
        self.assertEqual(action.outcome, "Already completed")

    def test_template_renders_edit_controls_only_for_in_flight_actions(self):
        selected = self._action(StrategyAction.ActionStatus.SELECTED)
        executed = self._action(StrategyAction.ActionStatus.EXECUTED)
        self.client.force_login(self.officer)
        response = self.client.get(
            reverse(
                "remedial_strategy_detail",
                args=[self.account.loan_id, self.strategy.strategy_id],
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Only the SELECTED (in-flight, skippable) action is editable; the
        # EXECUTED action gets neither an update nor a skip control.
        self.assertEqual(content.count('value="update"'), 1)
        self.assertEqual(content.count('value="skip"'), 1)

    def test_view_update_and_skip(self):
        action = self._action(StrategyAction.ActionStatus.SELECTED)
        url = reverse(
            "remedial_strategy_detail",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )
        self.client.force_login(self.officer)
        response = self.client.post(
            url,
            {
                "action": "update",
                "action_id": action.action_id,
                "assignee": "Zoe",
                "due_date": "2026-12-01",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        action.refresh_from_db()
        self.assertEqual(action.assignee, "Zoe")
        self.assertEqual(action.due_date, datetime.date(2026, 12, 1))
        # Skip the same action.
        response = self.client.post(
            url,
            {
                "action": "skip",
                "action_id": action.action_id,
                "outcome": "Borrower already paid",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        action.refresh_from_db()
        self.assertEqual(action.status, StrategyAction.ActionStatus.SKIPPED)
        self.assertEqual(action.outcome, "Borrower already paid")

    def test_board_member_update_post_is_rejected(self):
        board = User.objects.create_user(
            username="board-edit", password="pass", role=User.Role.BOARD_MEMBER
        )
        self.client.force_login(board)
        action = self._action(StrategyAction.ActionStatus.SELECTED)
        response = self.client.post(
            reverse(
                "remedial_strategy_detail",
                args=[self.account.loan_id, self.strategy.strategy_id],
            ),
            {
                "action": "update",
                "action_id": action.action_id,
                "assignee": "Nope",
                "due_date": "",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        action.refresh_from_db()
        self.assertEqual(action.assignee, "")
