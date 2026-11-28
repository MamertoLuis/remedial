"""Demo database provisioning (see specs/demo-data/spec.md).

Composes the existing ad-hoc loaders with a cascade-driven timeline so a
seeded demo behaves like production: exposures are upserted in date order
through the service layer, so delinquency, account status, the escalation
ladder, and ECL provisions are all derived rather than hardcoded.

The command refuses to run on a database holding organic (non-demo) exposure
or delinquency rows: real imports never run on a demo host.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

from .main import upsert_exposure
from ..models import (
    DelinquencyStatus,
    ECLProvisionHistory,
    EscalationState,
    Exposure,
    LitigationEntry,
    LoanAccount,
    RemedialStrategy,
)

#: The demo portfolio's account set (created by ``load_dummy_data``).
DEMO_ACCOUNT_IDS = tuple(f"ACC{n:03d}" for n in range(1, 11))

#: Deterministic demo users, one per production role. ``admin`` may already
#: exist from ``start_db.sh``; the seed resets it to the demo password.
DEMO_USERS = {
    "demo-officer": "ACCOUNT_OFFICER",
    "demo-manager": "MANAGER",
    "demo-board": "BOARD_MEMBER",
    "admin": "SYSTEM_ADMINISTRATOR",
}
DEMO_PASSWORD = "demo-password-123"

#: Weekly snapshots per account (bounded dataset: 10 accounts x 16 = 160 rows).
WEEKS = 16
SNAPSHOT_DAYS = 7


# --------------------------------------------------------------------------- #
# Organic-data boundary
# --------------------------------------------------------------------------- #


def ensure_organic_free() -> None:
    """Refuse to seed when exposure/delinquency rows exist outside the demo set.

    Runs before any write so a demo host can never mix real-sourced data
    (iAccs imports or CSV imports) into the fake portfolio.
    """
    organic = (
        Exposure.objects.exclude(account__loan_id__in=DEMO_ACCOUNT_IDS).exists()
        or DelinquencyStatus.objects.exclude(
            account__loan_id__in=DEMO_ACCOUNT_IDS
        ).exists()
    )
    if organic:
        raise CommandError(
            "seed_demo refuses to run: this database holds exposure or "
            "delinquency records for accounts outside the demo set "
            f"({', '.join(DEMO_ACCOUNT_IDS)}). Real imports "
            "(import_from_iaccs, CSV imports) must never run on a demo host. "
            "Start from a fresh database or remove the organic rows first."
        )


# --------------------------------------------------------------------------- #
# Demo users
# --------------------------------------------------------------------------- #


def seed_users() -> None:
    """Create or reset one demo user per production role (deterministic)."""
    User = get_user_model()
    for username, role in DEMO_USERS.items():
        user, _ = User.objects.get_or_create(
            username=username, defaults={"email": f"{username}@example.com"}
        )
        user.role = role
        user.set_password(DEMO_PASSWORD)
        user.is_staff = role == "SYSTEM_ADMINISTRATOR"
        user.is_superuser = role == "SYSTEM_ADMINISTRATOR"
        user.save()


# --------------------------------------------------------------------------- #
# Designed account narratives
# --------------------------------------------------------------------------- #

#: DPD per weekly snapshot, oldest (week 0) to newest (week WEEKS-1).
ARCS: dict = {
    "performing": [0] * WEEKS,
    "deteriorating": [min(7 * i, 120) for i in range(WEEKS)],
    "cured": [8 * i if i < 8 else 0 for i in range(WEEKS)],
    "chronic-npl": [min(40 + 13 * i, 240) for i in range(WEEKS)],
    "written-off": [min(8 * i, 120) for i in range(WEEKS)],
    "litigation": [min(6 * i + 10, 95) for i in range(WEEKS)],
}

#: Accounts are assigned arcs in loan-id order and may repeat.
ARC_ORDER = [
    "performing",
    "deteriorating",
    "cured",
    "chronic-npl",
    "written-off",
    "litigation",
]

_WRITE_OFF_SENTINEL = Decimal("1.00")


def _arc_for_index(index: int) -> str:
    return ARC_ORDER[index % len(ARC_ORDER)]


def _snapshot_balance(
    account: LoanAccount, week: int, arc: str, rng: random.Random
) -> Decimal:
    """Principal outstanding for a snapshot, declining over the timeline."""
    if arc == "written-off" and week == WEEKS - 1:
        return _WRITE_OFF_SENTINEL
    if arc == "performing":
        factor = 0.98 - 0.01 * week
    else:
        factor = 1.0 - 0.01 * week
    jitter = rng.uniform(0.98, 1.0)
    value = float(account.original_principal) * factor * jitter
    return Decimal(str(round(value, 2)))


def _snapshot_accruals(principal: Decimal, week: int, dpd: int) -> tuple:
    """Small accrued interest/penalty figures so the demo reads realistically."""
    interest = round(float(principal) * 0.001 * (week + 1), 2)
    penalty = round(dpd * 5.0, 2)
    return Decimal(str(interest)), Decimal(str(penalty))


# --------------------------------------------------------------------------- #
# Cascade timeline
# --------------------------------------------------------------------------- #


def prepare_demo_accounts() -> None:
    """Purge state written by a previous seed so re-runs are clean."""
    accounts = LoanAccount.objects.filter(loan_id__in=DEMO_ACCOUNT_IDS)
    Exposure.objects.filter(account__in=accounts).delete()
    DelinquencyStatus.objects.filter(account__in=accounts).delete()
    EscalationState.objects.filter(account__in=accounts).delete()
    ECLProvisionHistory.objects.filter(exposure__account__in=accounts).delete()
    LitigationEntry.objects.filter(account__in=accounts).delete()
    RemedialStrategy.objects.filter(account__in=accounts).delete()


def run_timeline(accounts, rng: random.Random) -> None:
    """Write each account's arc as weekly snapshots through the cascade.

    Snapshots are upserted oldest to newest so every derived consequence
    (delinquency, status, escalation ladder, ECL) evolves in date order.
    """
    today = date.today()
    for index, account in enumerate(accounts):
        arc = _arc_for_index(index)
        series = ARCS[arc]
        for week, dpd in enumerate(series):
            as_of = today - timedelta(days=(WEEKS - 1 - week) * SNAPSHOT_DAYS)
            principal = _snapshot_balance(account, week, arc, rng)
            interest, penalty = _snapshot_accruals(principal, week, dpd)
            upsert_exposure(
                account=account,
                as_of_date=as_of,
                defaults={
                    "principal_outstanding": principal,
                    "accrued_interest": interest,
                    "accrued_penalty": penalty,
                    "days_past_due": dpd,
                    "snapshot_type": "EVENT",
                    "source": "CSV",
                },
            )


def seed_litigation(accounts) -> LitigationEntry:
    """Raise and approve a litigation entry on the 'litigation' arc account."""
    User = get_user_model()
    officer = User.objects.get(username="demo-officer")
    manager = User.objects.get(username="demo-manager")

    litigation_account = None
    for index, account in enumerate(accounts):
        if _arc_for_index(index) == "litigation":
            litigation_account = account
            break
    if litigation_account is None:
        raise CommandError("No litigation-arc account found to seed.")

    from .litigation_service import approve_litigation_entry, raise_litigation_entry

    entry = raise_litigation_entry(
        account=litigation_account,
        strategy_type="Legal Action",
        start_date=date.today() - timedelta(days=30),
        rationale=(
            "Demo narrative: account in legal proceedings; seeded for the demo."
        ),
        officer=officer,
    )
    approve_litigation_entry(entry, approver=manager, notes="Demo approval")
    return entry