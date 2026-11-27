"""
Account-level litigation entry service.

Owns the raise / approve / reject lifecycle for an account-level litigation
entry (a record that an account is entering, or has entered, legal action).
Only an ACCOUNT_OFFICER may raise an entry; only a MANAGER may approve or
reject it. The approved entry satisfies the Legal Action / Foreclosure
strategy entry gate (see ``strategy_service._check_entry_gates``).
"""
from django.core.exceptions import ValidationError
from django.utils import timezone

from users.models import User

from ..models import LitigationEntry


# Strategy types a litigation entry can target.
LITIGATION_STRATEGY_TYPES = ("Legal Action", "Foreclosure")
# Statuses that count as "one active entry" per account.
ACTIVE_STATUSES = [LitigationEntry.Status.PENDING_APPROVAL, LitigationEntry.Status.APPROVED]


class LitigationEntryError(ValidationError):
    """Raised when a litigation entry transition is invalid."""


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------


def _require_officer(user):
    if user is None or user.role != User.Role.ACCOUNT_OFFICER:
        raise LitigationEntryError(
            "Only ACCOUNT_OFFICER users may raise a litigation entry."
        )


def _require_manager(user):
    if user is None or user.role != User.Role.MANAGER:
        raise LitigationEntryError(
            "Only MANAGER users may approve or reject a litigation entry."
        )


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def get_active_entry(account):
    """Return the account's single active (pending or approved) entry, or None."""
    return (
        LitigationEntry.objects.filter(account=account, status__in=ACTIVE_STATUSES)
        .order_by("-raised_at")
        .first()
    )


def has_approved_litigation_entry(account):
    """True when the account holds an APPROVED litigation entry."""
    return LitigationEntry.objects.filter(
        account=account, status=LitigationEntry.Status.APPROVED
    ).exists()


def get_pending_entries():
    """Return all PENDING_APPROVAL entries across accounts (manager queue)."""
    return LitigationEntry.objects.filter(
        status=LitigationEntry.Status.PENDING_APPROVAL
    ).order_by("raised_at")


# ---------------------------------------------------------------------------
# Raise
# ---------------------------------------------------------------------------


def raise_litigation_entry(*, account, strategy_type, start_date, rationale, officer):
    """
    Raise an account-level litigation entry for the given account.

    Only an ACCOUNT_OFFICER may raise. The entry is created in
    PENDING_APPROVAL and is never derived from delinquency. At most one
    active (PENDING_APPROVAL or APPROVED) entry may exist per account, so a
    second raise is declined while one is active. Returns the new entry.
    """
    _require_officer(officer)
    if strategy_type not in LITIGATION_STRATEGY_TYPES:
        raise LitigationEntryError(
            "A litigation entry must target Legal Action or Foreclosure."
        )
    if not rationale:
        raise LitigationEntryError(
            "A litigation entry requires an officer rationale."
        )
    if not start_date:
        raise LitigationEntryError(
            "A litigation entry requires a litigation start date."
        )
    if get_active_entry(account) is not None:
        raise LitigationEntryError(
            "Account already has an active litigation entry."
        )

    return LitigationEntry.objects.create(
        account=account,
        strategy_type=strategy_type,
        start_date=start_date,
        rationale=rationale,
        status=LitigationEntry.Status.PENDING_APPROVAL,
        raised_by=officer,
        created_by=officer,
        updated_by=officer,
    )


# ---------------------------------------------------------------------------
# Approve / reject
# ---------------------------------------------------------------------------


def _decide(entry, approver, notes, new_status):
    _require_manager(approver)
    if entry.status != LitigationEntry.Status.PENDING_APPROVAL:
        raise LitigationEntryError(
            f"Cannot decide a litigation entry in status {entry.status}."
        )
    entry.status = new_status
    entry.decided_by = approver
    entry.decided_at = timezone.now()
    entry.decision_notes = notes or ""
    entry.updated_by = approver
    entry.save(
        update_fields=[
            "status",
            "decided_by",
            "decided_at",
            "decision_notes",
            "updated_by",
            "updated_at",
        ]
    )
    return entry


def approve_litigation_entry(entry, *, approver, notes=""):
    """Approve a pending litigation entry (MANAGER only)."""
    return _decide(entry, approver, notes, LitigationEntry.Status.APPROVED)


def reject_litigation_entry(entry, *, approver, notes=""):
    """Reject a pending litigation entry (MANAGER only); allows a re-raise."""
    return _decide(entry, approver, notes, LitigationEntry.Status.REJECTED)