"""Canonical identity mapping and field derivation for iAccs loans.

Conventions mirror ``URBD_Financial_Analytics/references/loan-source-to-target-mapping.md``:

* Loans are SL class ``SLC_CODE = 12``.
* The loan key is five-part: ``(BR_CODE, SLC_CODE=12, SLT_CODE, REF_NO, CLIENTID)``.
* Outstanding principal is not stored; it is ``SUM(sldtl.AMT)`` over
  ``SLE_CODE=11`` (disbursements positive, repayments negative).
* Days past due (DPD) is not stored; it is computed from the repayment
  schedule with the aggregate-shortfall rule (see
  :func:`compute_schedule_dpd`).
* Deferrals carry no duration in ``deferdate``, so no day offset is applied.

All functions here are pure and unit-testable without a database connection.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- #
# iAccs conventions (from the URBD mapping document)
# --------------------------------------------------------------------------- #

LOAN_SLC_CODE = 12
SLE_PRINCIPAL = 11
SLE_INTEREST_PAID = 23
SLE_PENALTY = 41
#: Collection receipt trunk codes that reduce principal/interest/penalty.
COLLECTION_TR_CODES = (10, 12, 15)
APPROVED_STATUSES = frozenset((3, 7))  # loanappstatus: 3=Approved, 7=Released


def render_loan_id(br_code: int, slt_code: int, ref_no: int, client_id: int) -> str:
    """Render the canonical five-part loan key as the Django ``loan_id``.

    Example: ``(1, 8, 1428, 1289)`` -> ``"01-12-08-1428-1289"``.
    """
    return (
        f"{int(br_code):02d}-{LOAN_SLC_CODE}-"
        f"{int(slt_code):02d}-{int(ref_no)}-{int(client_id)}"
    )


def render_borrower_id(branch_code: int, client_id: int) -> str:
    """Render the borrower id from the ``(ClientIDBrCode, ClientID)`` key.

    A single branch is live today, so the id is the client number itself;
    the branch is kept in the signature so a multi-branch render
    (``"{br}-{client}"``) can be introduced without touching callers.
    """
    return str(int(client_id))


def compute_schedule_dpd(
    schedule: Sequence[Tuple[date, Decimal]],
    principal_repaid: Decimal,
    cutoff: date,
    defer_days: int = 0,
) -> int:
    """Aggregate days-past-due from the repayment schedule and total repaid.

    Each installment has an amount due on a due date. Walk the schedule in
    order, accumulating scheduled principal due; the oldest installment not
    fully covered by the principal the borrower has repaid is the first one
    where the cumulative scheduled principal due exceeds ``principal_repaid``.
    DPD = ``(cutoff - that due date).days - defer_days``, floored at 0, and
    only counted when that due date has arrived (``<= cutoff``).

    This is the audit-friendly "aggregate shortfall" basis used by the URBD
    analysis scripts (``URBD_Financial_Analytics/scripts/loan_data.py``).
    """
    schedule = [item for item in schedule if item[0] <= cutoff]
    if not schedule:
        return 0

    repaid = float(principal_repaid or Decimal("0"))
    cumulative = 0.0
    oldest_unpaid: Optional[date] = None
    for item in schedule:
        due_date, principal_due = item[0], item[1]
        cumulative += float(principal_due or Decimal("0"))
        if cumulative > repaid + 0.001 and oldest_unpaid is None:
            oldest_unpaid = due_date

    if oldest_unpaid is None:
        return 0
    days = (cutoff - oldest_unpaid).days - defer_days
    return max(0, days)


def build_borrower_defaults(master: dict) -> dict:
    """Map an iAccs loan master row to ``upsert_borrower`` defaults."""
    return {
        "borrower_type": "PERSON",
        "full_name": (master.get("client_name") or "").strip() or "UNKNOWN",
        "primary_address": "",
        "mobile": "",
        "borrower_group": None,
    }


def build_loan_defaults(master: dict, borrower) -> dict:
    """Map an iAccs loan master row to ``upsert_loan_account`` defaults."""
    release_date = master.get("release_date")
    approval_date = master.get("approval_date")
    principal = _money(master.get("principal_approved"))
    rate = _rate(master.get("interest_rate"))
    product = (master.get("product") or "").strip()
    return {
        "borrower": borrower,
        "booking_date": release_date or approval_date or date(1900, 1, 1),
        "maturity_date": master.get("maturity_date") or date(1900, 1, 1),
        "original_principal": principal,
        "interest_rate": rate,
        "loan_type": product[:50] or f"SLC-{LOAN_SLC_CODE}",
        "account_officer_id": "",
        "status": "PERFORMING",
    }


def build_exposure_defaults(
    master: dict,
    agg: dict,
    schedule: Sequence[Tuple[date, Decimal, Decimal]],
    cutoff: date,
) -> dict:
    """Map aggregates + schedule to ``upsert_exposure`` defaults.

    ``agg`` carries ``outstanding`` (principal), ``total_advanced`` and
    ``interest_collected`` (mirrored from ``sldtl`` aggregates).  Interest
    receivable is the schedule-based accrual estimate: scheduled interest due
    through the cutoff minus interest collected, floored at 0 (accrued
    interest per loan is not stored in iAccs).
    """
    outstanding = _money(agg.get("outstanding"))
    advanced = _money(agg.get("total_advanced"))
    repaid = Decimal(advanced) - Decimal(outstanding)
    dpd = compute_schedule_dpd(schedule, repaid, cutoff)

    sched_int = Decimal("0.00")
    for due_date, _, interest_due in schedule:
        if due_date <= cutoff:
            sched_int += Decimal(interest_due or 0)
    interest_collected = _money(agg.get("interest_collected"))
    interest_receivable = max(Decimal("0.00"), sched_int - interest_collected)

    return {
        "principal_outstanding": outstanding,
        "accrued_interest": interest_receivable,
        "accrued_penalty": Decimal("0.00"),
        "days_past_due": dpd,
        "snapshot_type": "EVENT",
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _money(value) -> Decimal:
    """Coerce a DB value to a 2-decimal Decimal, tolerating None/str/float."""
    if value is None:
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (ValueError, ArithmeticError):
        return Decimal("0.00")


def _rate(value) -> Decimal:
    """Coerce an interest rate to a 2-decimal Decimal."""
    if value is None:
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (ValueError, ArithmeticError):
        return Decimal("0.00")