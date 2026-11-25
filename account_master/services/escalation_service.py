"""
Notice escalation ladder service (judgment plane).

Owns every ladder transition: start, advance/issue, pause/resume on
promise-to-pay, close on cure/arrangement/terminal, and the idempotent
fact-plane hook used by the snapshot path. Models stay thin; all due-date
math and lifecycle rules live here.
"""
from datetime import timedelta

from django.utils import timezone

from ..models import (
    EscalationStage,
    EscalationState,
    Notice,
    RemedialStrategy,
)

# Statuses that count as "one open position" for a loan account.
OPEN_STATUSES = ["PENDING", "ACTIVE", "PAUSED"]
# Mirrored LoanAccount.status values that mean the account is delinquent.
DELINQUENT_STATUSES = {"PAST_DUE", "NPL"}
# Mirrored status that means the account returned to performing (cure).
CURED_STATUS = "PERFORMING"
# Restructuring strategy type counts as an arrangement for close-on-arrangement.
RESTRUCTURING_STRATEGY_TYPE = "Restructuring"
TERMINAL_STRATEGY_TYPES = ("Legal Action", "Foreclosure")


class EscalationError(ValueError):
    """Raised when a ladder transition is invalid."""


# ---------------------------------------------------------------------------
# Position lookup
# ---------------------------------------------------------------------------


def get_open_state(account):
    """Return the account's single open escalation state, or None."""
    return (
        EscalationState.objects.filter(account=account, status__in=OPEN_STATUSES)
        .select_related("current_stage")
        .order_by("-stage_started_on")
        .first()
    )


def get_first_stage():
    """Return the first (stage_no 1) stage of the fixed ladder template."""
    return EscalationStage.objects.order_by("stage_no").first()


def get_next_stage(stage):
    """Return the stage that follows ``stage`` in the template, or None."""
    return (
        EscalationStage.objects.filter(stage_no__gt=stage.stage_no)
        .order_by("stage_no")
        .first()
    )


def _normalize_stage(stage):
    if isinstance(stage, EscalationStage):
        return stage
    return EscalationStage.objects.get(pk=stage)


# ---------------------------------------------------------------------------
# Start / close
# ---------------------------------------------------------------------------


def start_escalation(account, *, user=None):
    """
    Create a PENDING escalation state at the first stage.

    Never creates a second open state for an account that already holds one
    (spec: "Each account tracks one escalation position").
    Returns ``(state, created)``.
    """
    open_state = get_open_state(account)
    if open_state is not None:
        return open_state, False

    first_stage = get_first_stage()
    if first_stage is None:
        raise EscalationError(
            "Cannot start escalation: no escalation stages are seeded."
        )

    state = EscalationState.objects.create(
        account=account,
        current_stage=first_stage,
        stage_started_on=timezone.now().date(),
        status=EscalationState.Status.PENDING,
        created_by=user,
        updated_by=user,
    )
    return state, True


def close_escalation(account, reason, *, user=None):
    """
    Close the account's open escalation state with the given reason
    (``cured`` / ``arrangement`` / ``terminal``). No further notice is
    scheduled: ``next_notice_due`` is cleared. Returns the closed state or
    None when no open state existed.
    """
    open_state = get_open_state(account)
    if open_state is None:
        return None

    reason = (
        EscalationState.CloseReason(reason)
        if isinstance(reason, str)
        else reason
    )
    open_state.status = EscalationState.Status.CLOSED
    open_state.closed_reason = reason
    open_state.next_notice_due = None
    open_state.updated_by = user
    open_state.save()
    return open_state


# ---------------------------------------------------------------------------
# Officer-driven advancement
# ---------------------------------------------------------------------------


def issue_notice(account, stage, method, user=None, *, issued_on=None):
    """
    Issue a notice at the account's current stage.

    Records a ``Notice``, then:
    - non-terminal stage: advances the state to the next stage, sets
      ``stage_started_on`` and computes ``next_notice_due = issued_on +
      duration_days`` of the *new* stage (spec: "sets the next-notice due
      date from the new stage's duration");
    - terminal stage: records the notice and CLOSES the state (reason
      "terminal"); no further notice is scheduled.

    Returns ``(notice, state)`` where ``state`` is the state after the
    transition (None when closed). Raises ``EscalationError`` when the
    account has no open state or ``stage`` does not match its current stage.
    """
    open_state = get_open_state(account)
    if open_state is None:
        raise EscalationError(
            f"Account {account.loan_id} has no open escalation state to issue a notice for."
        )

    stage = _normalize_stage(stage)
    if stage.pk != open_state.current_stage_id:
        raise EscalationError(
            "Notice stage must match the account's current escalation stage "
            f"({open_state.current_stage})."
        )

    issued_on = issued_on or timezone.now().date()
    notice = Notice.objects.create(
        account=account,
        stage=open_state.current_stage,
        issued_on=issued_on,
        method=method,
        issued_by=user,
    )

    if open_state.current_stage.is_terminal:
        close_escalation(account, EscalationState.CloseReason.TERMINAL, user=user)
        return notice, None

    next_stage = get_next_stage(open_state.current_stage)
    if next_stage is None:
        # Template drift guard: no further stage defined and current is not
        # terminal, so treat the last defined stage as the endpoint.
        close_escalation(account, EscalationState.CloseReason.TERMINAL, user=user)
        return notice, None

    open_state.current_stage = next_stage
    open_state.stage_started_on = issued_on
    open_state.status = EscalationState.Status.ACTIVE
    open_state.next_notice_due = issued_on + timedelta(days=next_stage.duration_days)
    open_state.updated_by = user
    open_state.save()
    return notice, open_state


def recommend_terminal(account, strategy_type, *, user=None):
    """
    Close the ladder with reason "terminal" and create an ACTIVE
    ``RemedialStrategy`` of type Legal Action or Foreclosure through the
    existing strategy creation path, so the one-active-strategy invariant
    and the supersede-orphaned-compromises rule apply unchanged.
    """
    if strategy_type not in TERMINAL_STRATEGY_TYPES:
        raise EscalationError(
            "Terminal recommendation must be 'Legal Action' or 'Foreclosure'."
        )

    close_escalation(account, EscalationState.CloseReason.TERMINAL, user=user)

    from .main import create_remedial_strategy  # local import to avoid a cycle

    strategy = create_remedial_strategy(
        account=account,
        strategy_type=strategy_type,
        strategy_start_date=timezone.now().date(),
        strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
    )
    strategy.created_by = user
    strategy.updated_by = user
    strategy.save(update_fields=["created_by", "updated_by", "updated_at"])
    return strategy


# ---------------------------------------------------------------------------
# Promise-to-pay pause / resume
# ---------------------------------------------------------------------------


def has_pending_ptp(account, *, as_of=None):
    """
    True when the account's most recent open promise-to-pay on the contact
    log is still pending, i.e. the latest activity row carrying a
    ``promise_to_pay_date`` has that date not yet reached. An honored or
    broken promise (date reached / row superseded) stops counting as
    pending, but never moves the stage — that is recorded on the contact
    log only.
    """
    as_of = as_of or timezone.now().date()
    latest_promise = (
        account.collection_activities.filter(promise_to_pay_date__isnull=False)
        .order_by("-activity_date", "-activity_id")
        .first()
    )
    if latest_promise is None:
        return False
    return latest_promise.promise_to_pay_date >= as_of


def pause_escalation(account, *, user=None):
    """Transition an ACTIVE state to PAUSED. Returns the state or None."""
    open_state = get_open_state(account)
    if open_state is None or open_state.status != EscalationState.Status.ACTIVE:
        return None
    open_state.status = EscalationState.Status.PAUSED
    open_state.updated_by = user
    open_state.save(update_fields=["status", "updated_by", "updated_at"])
    return open_state


def resume_escalation(account, *, user=None):
    """Transition a PAUSED state back to ACTIVE at the same stage."""
    open_state = get_open_state(account)
    if open_state is None or open_state.status != EscalationState.Status.PAUSED:
        return None
    open_state.status = EscalationState.Status.ACTIVE
    open_state.updated_by = user
    open_state.save(update_fields=["status", "updated_by", "updated_at"])
    return open_state


def sync_pause_state(account, *, user=None):
    """
    Re-derive the ACTIVE <-> PAUSED position from the contact log and apply
    the transition. Returns the open state (possibly with a new status) or
    None.
    """
    open_state = get_open_state(account)
    if open_state is None or open_state.status == EscalationState.Status.PENDING:
        return open_state
    if has_pending_ptp(account):
        if open_state.status == EscalationState.Status.ACTIVE:
            return pause_escalation(account, user=user)
    elif open_state.status == EscalationState.Status.PAUSED:
        return resume_escalation(account, user=user)
    return open_state


# ---------------------------------------------------------------------------
# Fact-plane hook (snapshot coupling)
# ---------------------------------------------------------------------------


def _has_active_arrangement(account):
    """True when the account holds an approved active arrangement."""
    if account.compromise_agreements.filter(status="ACTIVE").exists():
        return True
    return account.remedial_strategies.filter(
        strategy_type=RESTRUCTURING_STRATEGY_TYPE,
        strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
    ).exists()


def sync_escalation_on_snapshot(account, derived_status, *, user=None):
    """
    Idempotent fact-plane → ladder hook, called from the snapshot path in
    ``services/main.py`` after the loan account status is updated.

    - Arrangement approved (active CompromiseAgreement or Restructuring
      strategy) closes any open state with reason "arrangement".
    - Performing (cured) status closes any open state with reason "cured".
    - Delinquent status starts a PENDING ladder at stage 1 when no open
      state exists.
    - The PTP pause/resume position is re-derived for an open ACTIVE state.

    Repeat snapshots are safe: they never duplicate open states or wrongly
    transition a closed ladder.
    """
    if _has_active_arrangement(account):
        close_escalation(account, EscalationState.CloseReason.ARRANGEMENT, user=user)
    elif derived_status == CURED_STATUS:
        close_escalation(account, EscalationState.CloseReason.CURED, user=user)
    elif derived_status in DELINQUENT_STATUSES:
        start_escalation(account, user=user)

    sync_pause_state(account, user=user)
