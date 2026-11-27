"""Single source of truth for loan classification, aging buckets, and status.

Replaces the divergent derivations previously duplicated in
``account_master/services/main.py``, the legacy flat ``services.py``, and the
legacy management commands.

Business rules (see the portfolio-metrics spec):
- Past due is the umbrella: any loan with days past due >= 1 is past due, and
  NPL loans are past due by definition.
- NPL starts at **more than 90 days past due** (91+). A loan with exactly 90
  days past due is classified ``SM`` and maps to status ``PAST_DUE``.
"""

from decimal import Decimal

# Sentinel principal values that override classification-based status.
WRITEOFF_PRINCIPAL = Decimal("1.00")
CLOSED_PRINCIPAL = Decimal("0.00")

NPL_CLASSIFICATIONS = ("SS", "D", "L")


def derive_aging_bucket(days_past_due: int) -> str:
    """Return the aging bucket label for a days-past-due value."""
    if days_past_due == 0:
        return "Current"
    if days_past_due <= 30:
        return "1-30"
    if days_past_due <= 60:
        return "31-60"
    if days_past_due <= 90:
        return "61-90"
    if days_past_due <= 120:
        return "91-120"
    if days_past_due <= 180:
        return "121-180"
    if days_past_due <= 360:
        return "181-360"
    return "Over 360"


def derive_classification(days_past_due: int) -> str:
    """Derive the suggested classification from days past due.

    ``SM`` covers 1-90 days (a loan with exactly 90 days past due is past due
    but not yet NPL); ``SS`` starts at 91 days.
    """
    if days_past_due == 0:
        return "C"
    if days_past_due <= 90:
        return "SM"
    if days_past_due <= 180:
        return "SS"
    if days_past_due <= 360:
        return "D"
    return "L"


def derive_status(classification: str, outstanding_balance) -> str:
    """Map a classification (and exposure sentinels) to LoanAccount.status.

    ``outstanding_balance`` is the latest principal outstanding, or ``None``
    when no exposure exists. Sentinel balances (written off / closed) take
    precedence over the classification mapping.
    """
    if outstanding_balance == WRITEOFF_PRINCIPAL:
        return "WRITEOFF"
    if outstanding_balance == CLOSED_PRINCIPAL:
        return "CLOSED"
    if classification in NPL_CLASSIFICATIONS:
        return "NPL"
    if classification == "SM":
        return "PAST_DUE"
    return "PERFORMING"
