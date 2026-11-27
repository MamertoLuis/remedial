"""
Strategy framework service.

Owns every transition that carries cross-entity side effects (design D6):
recommendation creation with a required assessment snapshot, action
selection/execution, the manager-only approval workflow, officer-declared
failure, agreement rescind, and per-type completion transitions. Models stay
thin; ``RemedialStrategy.save()`` supersede behavior remains as a safety net.

Side effects triggered by approved actions (explicit, enumerable by catalog
code):
- ``WO-APPROVAL``          -> account status WRITEOFF (write-off booked)
- ``CP-RESCIND/RS-RESCIND``-> agreement RESCINDED + strategy CANCELLED
- ``CP-*`` settlement      -> compromise agreement activated (D7)
"""
from datetime import date as _date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from ..models import (
    CollectionActivityLog,
    Collateral,
    EscalationState,
    Guarantor,
    LoanAccount,
    RemedialStrategy,
    StrategyAction,
    StrategyActionCatalogEntry,
    StrategyApproval,
    StrategyAssessment,
)

# Strategy types that carry a repayment agreement and therefore a rescind path.
AGREEMENT_STRATEGY_TYPES = ("Compromise", "Restructuring")
# Catalog codes that end with RESCIND mark the rescind action template.
RESCIND_CODE_SUFFIX = "RESCIND"
# Write-off approval template code, with the account-booking side effect.
WRITEOFF_APPROVAL_CODE = "WO-APPROVAL"

COMPROMISE_FULLY_PAID_AGREEMENT_STATUS = "COMPLETED"
COMPROMISE_AGREEMENT_ACTIVATABLE_STATUSES = ["PENDING_APPROVAL", "ACTIVE"]


# ---------------------------------------------------------------------------
# Ladder / gate helpers
# ---------------------------------------------------------------------------


def _latest_escalation_state(account):
    return (
        EscalationState.objects.filter(account=account)
        .order_by("-stage_started_on", "-escalation_id")
        .first()
    )


def ladder_terminal_closed(account):
    """True when the account's ladder was closed at the terminal stage."""
    latest = _latest_escalation_state(account)
    return (
        latest is not None
        and latest.status == EscalationState.Status.CLOSED
        and latest.closed_reason == EscalationState.CloseReason.TERMINAL
    )


def approved_rescind_exists(account):
    """True when an agreement rescind on this account was approved."""
    return StrategyApproval.objects.filter(
        decision=StrategyApproval.Decision.APPROVED,
        action__catalog_entry__code__endswith=RESCIND_CODE_SUFFIX,
        action__strategy__account=account,
    ).exists()


def _check_entry_gates(account, strategy_type):
    """Enforce the Legal Action / Foreclosure entry gates (design D9)."""
    from .litigation_service import has_approved_litigation_entry  # local import to avoid a cycle

    if strategy_type not in ("Legal Action", "Foreclosure"):
        return
    if not (
        ladder_terminal_closed(account)
        or approved_rescind_exists(account)
        or has_approved_litigation_entry(account)
    ):
        raise ValidationError(
            "A Legal Action / Foreclosure recommendation requires the escalation "
            "ladder's terminal stage, an approved agreement rescind, or an "
            "approved litigation entry on the account. If the account is already "
            "in litigation, raise an account-level litigation entry for manager "
            "approval first."
        )
    if strategy_type == "Foreclosure" and account.loan_security != "SECURED":
        raise ValidationError("Foreclosure requires a SECURED account.")


def _require_manager(user):
    """Only the MANAGER role may decide approvals (spec: manager sole approver)."""
    from users.models import User

    if user is None or user.role != User.Role.MANAGER:
        raise ValidationError("Only MANAGER users may approve or reject actions.")


# ---------------------------------------------------------------------------
# Assessment snapshot
# ---------------------------------------------------------------------------


def _copy_snapshot_fields(account, as_of_date):
    """Copy latest delinquency / exposure / collection history values."""
    delinquency = (
        account.delinquency_statuses.filter(as_of_date__lte=as_of_date)
        .order_by("-as_of_date")
        .first()
    )
    exposure = (
        account.exposures.filter(as_of_date__lte=as_of_date)
        .order_by("-as_of_date")
        .first()
    )
    activities = (
        account.collection_activities.filter(activity_date__lte=as_of_date)
        .order_by("-activity_date", "-activity_id")[:5]
    )
    summary = "; ".join(
        f"{a.activity_date.isoformat()}: {a.activity_type}"
        + (f" - {a.remarks[:80]}" if a.remarks else "")
        for a in activities
    )
    return {
        "days_past_due": delinquency.days_past_due if delinquency else 0,
        "aging_bucket": delinquency.aging_bucket or "" if delinquency else "",
        "classification": delinquency.classification or "" if delinquency else "",
        "outstanding_exposure": (
            exposure.total_exposure if exposure else Decimal("0.00")
        ),
        "collection_history_summary": summary,
    }


def _create_assessment(strategy, officer, assessment):
    """Persist the assessment snapshot for a strategy recommendation."""
    as_of_date = assessment.get("as_of_date") or strategy.strategy_start_date
    snapshot = _copy_snapshot_fields(strategy.account, as_of_date)
    strategy_assessment = StrategyAssessment.objects.create(
        strategy=strategy,
        as_of_date=as_of_date,
        officer_rationale=assessment["officer_rationale"],
        financial_condition=assessment.get("financial_condition", "ADEQUATE"),
        financial_condition_note=assessment.get("financial_condition_note", ""),
        willingness_to_pay=assessment.get("willingness_to_pay", "MEDIUM"),
        willingness_note=assessment.get("willingness_note", ""),
        recovery_outlook=assessment.get("recovery_outlook", "MEDIUM"),
        recovery_assessment_note=assessment.get("recovery_assessment_note", ""),
        expected_recovery=assessment.get("expected_recovery"),
        created_by=officer,
        updated_by=officer,
        **snapshot,
    )
    guarantor_ids = list(assessment.get("guarantors") or [])
    collateral_ids = list(assessment.get("collaterals") or [])
    if guarantor_ids:
        strategy_assessment.guarantors.set(
            Guarantor.objects.filter(pk__in=guarantor_ids, account=strategy.account)
        )
    if collateral_ids:
        strategy_assessment.collaterals.set(
            Collateral.objects.filter(pk__in=collateral_ids, account=strategy.account)
        )
    return strategy_assessment


# ---------------------------------------------------------------------------
# Recommendation creation
# ---------------------------------------------------------------------------


@transaction.atomic
def create_strategy_recommendation(
    *, account, strategy_type, strategy_start_date, officer, assessment
):
    """
    Create an ACTIVE strategy directly from the officer's recommendation with
    a required assessment snapshot (spec: recommendation activates the
    strategy; a recommendation requires an officer rationale).

    One ACTIVE strategy per account is preserved by ``RemedialStrategy.save()``
    (competing active strategy is superseded). Entry gates run here.
    """
    if strategy_type in ("Legal Action", "Foreclosure"):
        _check_entry_gates(account, strategy_type)
    if not assessment.get("officer_rationale"):
        raise ValidationError(
            "A strategy recommendation requires an officer rationale."
        )

    strategy = RemedialStrategy.objects.create(
        account=account,
        strategy_type=strategy_type,
        strategy_start_date=strategy_start_date,
        strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        created_by=officer,
        updated_by=officer,
    )
    _create_assessment(strategy, officer, assessment)
    return strategy


@transaction.atomic
def recommend_next_strategy(
    *, account, strategy_type, strategy_start_date, officer, assessment
):
    """
    Escalation-aware recommendation: only allowed after the current strategy
    exited (COMPLETED or CANCELLED); records a fresh assessment snapshot.
    """
    if account.remedial_strategies.filter(
        strategy_status=RemedialStrategy.StrategyStatus.ACTIVE
    ).exists():
        raise ValidationError(
            "A new strategy cannot be recommended while the current strategy "
            "is still active."
        )
    return create_strategy_recommendation(
        account=account,
        strategy_type=strategy_type,
        strategy_start_date=strategy_start_date,
        officer=officer,
        assessment=assessment,
    )


# ---------------------------------------------------------------------------
# Action selection / execution
# ---------------------------------------------------------------------------


def get_action_catalog(strategy):
    """The active strategy's own action catalog (template entries)."""
    return StrategyActionCatalogEntry.objects.filter(
        strategy_type=strategy.strategy_type
    )


@transaction.atomic
def select_action(*, strategy, catalog_entry, assignee="", due_date=None, officer=None):
    """
    Select an action from the strategy's own catalog. A gated action is held
    in PENDING_APPROVAL immediately; a non-gated action stays SELECTED until
    the officer executes it directly.
    """
    if isinstance(catalog_entry, int):
        catalog_entry = StrategyActionCatalogEntry.objects.get(pk=catalog_entry)
    if catalog_entry.strategy_type != strategy.strategy_type:
        raise ValidationError(
            "Only actions from the active strategy's own catalog may be selected."
        )
    return StrategyAction.objects.create(
        catalog_entry=catalog_entry,
        strategy=strategy,
        assignee=assignee,
        due_date=due_date,
        status=(
            StrategyAction.ActionStatus.PENDING_APPROVAL
            if catalog_entry.requires_approval
            else StrategyAction.ActionStatus.SELECTED
        ),
        created_by=officer,
        updated_by=officer,
    )


def execute_action(*, action, outcome, assignee=None, executed_on=None, officer=None):
    """
    Execute an action. Gated actions are blocked until approved; non-gated
    actions execute directly (spec: gated action cannot be executed before
    approval; officer executes a non-gated action directly).
    """
    action.execute(outcome=outcome, assignee=assignee, executed_on=executed_on)
    action.updated_by = officer
    action.save(update_fields=["updated_by", "updated_at"])
    return action


@transaction.atomic
def execute_action_and_log_activity(
    *,
    action,
    outcome,
    activity_type,
    remarks,
    executed_on=None,
    officer=None,
    staff_assigned="",
):
    """Log the evidence activity and execute the action in one transaction.

    Creates a collection activity for the strategy's account, links it to the
    action as evidence, and executes the action (approval-gated actions still
    require APPROVED status). Returns ``{"action": ..., "activity": ...}``.
    """
    executed = executed_on
    if isinstance(executed_on, str) and executed_on:
        executed = _date.fromisoformat(executed_on)
    account = action.strategy.account
    activity = CollectionActivityLog.objects.create(
        account=account,
        activity_date=executed or timezone.now().date(),
        activity_type=activity_type,
        remarks=remarks,
        action=action,
        staff_assigned=staff_assigned,
        created_by=officer,
        updated_by=officer,
    )
    # execute_action applies the action's own state machine (gated actions
    # raise unless APPROVED) within the same transaction.
    execute_action(
        action=action,
        outcome=outcome,
        executed_on=executed,
        officer=officer,
    )
    return {"action": action, "activity": activity}


# Terminal action statuses: once reached, planning fields and outcome are locked.
TERMINAL_ACTION_STATUSES = [
    StrategyAction.ActionStatus.EXECUTED,
    StrategyAction.ActionStatus.SKIPPED,
    StrategyAction.ActionStatus.REJECTED,
]


def update_action_planning(*, action, assignee="", due_date=None, officer=None):
    """Edit an action's planning fields while it is not terminal.

    ``assignee`` and ``due_date`` may be changed while the action is in
    SELECTED, PENDING_APPROVAL, or APPROVED. Once the action is EXECUTED,
    SKIPPED, or REJECTED the fields are locked. No outcome is accepted here,
    keeping the outcome lock structural (only execute/skip write outcome).
    """
    if action.status in TERMINAL_ACTION_STATUSES:
        raise ValidationError(
            f"Planning fields cannot be edited on a "
            f"{action.get_status_display()} action."
        )
    action.assignee = assignee
    action.due_date = due_date
    action.updated_by = officer
    action.save(
        update_fields=["assignee", "due_date", "updated_by", "updated_at"]
    )
    return action


def skip_action(*, action, outcome="", officer=None):
    """Skip a non-pending, non-terminal action, recording a reason.

    Reuses the model's ``skip``, which allows SELECTED (non-gated) and
    APPROVED (gated) actions and rejects PENDING_APPROVAL, REJECTED,
    EXECUTED, and already-SKIPPED actions.
    """
    action.skip(outcome=outcome)
    action.updated_by = officer
    action.save(update_fields=["updated_by", "updated_at"])
    return action


# ---------------------------------------------------------------------------
# Approval workflow (manager sole approver; board read-only)
# ---------------------------------------------------------------------------


@transaction.atomic
def approve_action(*, action, approver, comments="", conditions=""):
    """Approve a pending gated action and apply its side effects (D6)."""
    _require_manager(approver)
    if action.status != StrategyAction.ActionStatus.PENDING_APPROVAL:
        raise ValidationError("Only pending actions can be approved.")
    StrategyApproval.objects.create(
        action=action,
        approver=approver,
        decision=StrategyApproval.Decision.APPROVED,
        comments=comments,
        conditions=conditions,
        created_by=approver,
        updated_by=approver,
    )
    action.mark_approved()
    action.updated_by = approver
    action.save(update_fields=["updated_by", "updated_at"])
    _apply_approved_side_effects(action, approver)
    return action


@transaction.atomic
def reject_action(*, action, approver, comments=""):
    """Reject a pending gated action; a rejected action is not executed."""
    _require_manager(approver)
    if action.status != StrategyAction.ActionStatus.PENDING_APPROVAL:
        raise ValidationError("Only pending actions can be rejected.")
    StrategyApproval.objects.create(
        action=action,
        approver=approver,
        decision=StrategyApproval.Decision.REJECTED,
        comments=comments,
        created_by=approver,
        updated_by=approver,
    )
    action.mark_rejected()
    action.updated_by = approver
    action.save(update_fields=["updated_by", "updated_at"])
    return action


def list_pending_approvals():
    """Pending gated actions across accounts (manager approval queue)."""
    return (
        StrategyAction.objects.filter(
            status=StrategyAction.ActionStatus.PENDING_APPROVAL
        )
        .select_related("catalog_entry", "strategy", "strategy__account")
        .order_by("action_id")
    )


# ---------------------------------------------------------------------------
# Approval side effects (design D6/D7)
# ---------------------------------------------------------------------------


def _apply_approved_side_effects(action, approver):
    code = action.catalog_entry.code
    if code == WRITEOFF_APPROVAL_CODE:
        _book_writeoff(action, approver)
    elif code.endswith(RESCIND_CODE_SUFFIX) and code.startswith(("CP-", "RS-")):
        _apply_rescind(action, approver)
    elif code.startswith("CP-"):
        _activate_compromise_agreement(action, approver)


def _book_writeoff(action, approver):
    """Approved write-off action books the account as WRITEOFF."""
    account = action.strategy.account
    account.status = LoanAccount.LOAN_STATUS_CHOICES[3][0]  # "WRITEOFF"
    account.updated_by = approver
    account.save(update_fields=["status", "updated_by", "updated_at"])
    action.strategy.strategy_outcome = "Write-off booked."
    action.strategy.updated_by = approver
    action.strategy.save(
        update_fields=["strategy_outcome", "updated_by", "updated_at"]
    )


def _activate_compromise_agreement(action, approver):
    """Approved compromise settlement activates the agreement (D7)."""
    agreement = (
        action.strategy.compromise_agreements.filter(
            status__in=COMPROMISE_AGREEMENT_ACTIVATABLE_STATUSES
        )
        .order_by("-created_at")
        .first()
    )
    if agreement is None:
        return
    if agreement.status != "ACTIVE":
        agreement.status = "ACTIVE"
        agreement.updated_by = approver
        agreement.save(update_fields=["status", "updated_by", "updated_at"])


def _apply_rescind(action, approver):
    """Approved rescind: agreement RESCINDED, strategy CANCELLED."""
    strategy = action.strategy
    agreement = (
        strategy.compromise_agreements.exclude(status="SUPERSEDED")
        .order_by("-created_at")
        .first()
    )
    if agreement is not None:
        agreement.status = "RESCINDED"
        agreement.updated_by = approver
        agreement.save(update_fields=["status", "updated_by", "updated_at"])
    strategy.strategy_status = RemedialStrategy.StrategyStatus.CANCELLED
    strategy.strategy_outcome = "Agreement rescinded with approval."
    strategy.updated_by = approver
    strategy.save(
        update_fields=["strategy_status", "strategy_outcome", "updated_by", "updated_at"]
    )


# ---------------------------------------------------------------------------
# Officer-declared failure and rescind opening
# ---------------------------------------------------------------------------


@transaction.atomic
def declare_failure(*, strategy, officer, outcome="", unmet_conditions_note=""):
    """
    Officer declares the strategy failed.

    - Agreement-carrying strategies (Compromise / Restructuring): the
      agreement is marked UNSUCCESSFUL and a rescind action opens (gated).
      The strategy stays ACTIVE until the rescind is approved.
    - Non-agreement strategies: cancelled directly with the declared outcome
      (no rescind action).
    """
    if strategy.strategy_status != RemedialStrategy.StrategyStatus.ACTIVE:
        raise ValidationError("Only an ACTIVE strategy can be declared failed.")

    if strategy.strategy_type in AGREEMENT_STRATEGY_TYPES:
        agreement = (
            strategy.compromise_agreements.filter(
                status__in=[
                    "ACTIVE",
                    "PENDING_APPROVAL",
                    "UNSUCCESSFUL",
                ]
            )
            .order_by("-created_at")
            .first()
        )
        if agreement is not None:
            agreement.status = "UNSUCCESSFUL"
            agreement.updated_by = officer
            agreement.save(update_fields=["status", "updated_by", "updated_at"])
            _open_rescind_action(strategy, officer)
            if unmet_conditions_note:
                strategy.strategy_outcome = (
                    "Unmet approval conditions: " + unmet_conditions_note
                )
                strategy.updated_by = officer
                strategy.save(
                    update_fields=["strategy_outcome", "updated_by", "updated_at"]
                )
            return strategy

    strategy.strategy_status = RemedialStrategy.StrategyStatus.CANCELLED
    if outcome:
        strategy.strategy_outcome = outcome
    strategy.updated_by = officer
    strategy.save(
        update_fields=["strategy_status", "strategy_outcome", "updated_by", "updated_at"]
    )
    return strategy


def _open_rescind_action(strategy, officer):
    """Create a pending rescind action unless one is already open."""
    already_open = strategy.actions.filter(
        catalog_entry__code__endswith=RESCIND_CODE_SUFFIX,
        status__in=[
            StrategyAction.ActionStatus.PENDING_APPROVAL,
            StrategyAction.ActionStatus.APPROVED,
            StrategyAction.ActionStatus.SELECTED,
        ],
    ).exists()
    if already_open:
        return None
    rescind_entry = StrategyActionCatalogEntry.objects.filter(
        strategy_type=strategy.strategy_type, code__endswith=RESCIND_CODE_SUFFIX
    ).first()
    if rescind_entry is None:
        return None
    return select_action(strategy=strategy, catalog_entry=rescind_entry, officer=officer)


# ---------------------------------------------------------------------------
# Completion transitions (per strategy type)
# ---------------------------------------------------------------------------


def _is_agreement_fully_paid(agreement):
    installments = agreement.installments.all()
    if installments.exists():
        return not installments.exclude(status="PAID").exists()
    return agreement.status == COMPROMISE_FULLY_PAID_AGREEMENT_STATUS


def _has_executed_action(strategy, code=None):
    qs = strategy.actions.filter(
        status=StrategyAction.ActionStatus.EXECUTED
    )
    if code:
        qs = qs.filter(catalog_entry__code=code)
    return qs.exists()


def is_completion_condition_met(strategy):
    """True when the strategy type's completion condition is met (spec: 4.3)."""
    account = strategy.account
    strategy_type = strategy.strategy_type
    if strategy_type == "Intensive Collection":
        # Cures the account: back to performing status.
        return account.status == "PERFORMING"
    if strategy_type == "Restructuring":
        # Schedule honoured and the account cures.
        return account.status == "PERFORMING" and strategy.actions.filter(
            status=StrategyAction.ActionStatus.EXECUTED
        ).exists()
    if strategy_type == "Compromise":
        # Fully paid.
        agreement = strategy.compromise_agreements.order_by("-created_at").first()
        return agreement is not None and _is_agreement_fully_paid(agreement)
    if strategy_type == "Foreclosure":
        # Collateral liquidated/recovered.
        return account.status == "CLOSED" or _has_executed_action(
            strategy, "CR-DISPOSAL"
        )
    if strategy_type == "Legal Action":
        # Judgment or closure.
        return account.status == "CLOSED" or _has_executed_action(
            strategy, "LA-JUDGMENT-ENFORCEMENT"
        ) or _has_executed_action(strategy, "LA-ASSET-EXECUTION")
    if strategy_type == "Write-Off":
        # Write-off booked.
        return account.status == LoanAccount.LOAN_STATUS_CHOICES[3][0]
    return False


@transaction.atomic
def complete_strategy(*, strategy, outcome="", user=None):
    """Complete the strategy only when its type's completion condition holds."""
    if strategy.strategy_status != RemedialStrategy.StrategyStatus.ACTIVE:
        raise ValidationError("Only an ACTIVE strategy can be completed.")
    if not is_completion_condition_met(strategy):
        raise ValidationError(
            f"The completion condition for {strategy.strategy_type} is not met."
        )
    strategy.strategy_status = RemedialStrategy.StrategyStatus.COMPLETED
    if outcome:
        strategy.strategy_outcome = outcome
    strategy.updated_by = user
    strategy.save(
        update_fields=["strategy_status", "strategy_outcome", "updated_by", "updated_at"]
    )
    return strategy
