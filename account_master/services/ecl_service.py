from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction
from ..models import (
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    ECLProvisionHistory,
)


def _get_provision_rate_for_classification(
    classification: str, days_past_due: int
) -> Decimal:
    """
    Calculate ECL provision rate based on delinquency classification and days past due.

    IFRS 9 Staging:
    - Stage 1 (C/SM): 0-5% for 0-30 days past due
    - Stage 2 (SS/D): 20-50% for 31-90 days past due
    - Stage 3 (L): 100% for 91+ days past due

    Args:
        classification: Delinquency classification (C, SM, SS, D, L)
        days_past_due: Number of days the payment is past due

    Returns:
        Decimal: Provision rate (0.0 to 1.0)
    """

    # Convert to uppercase for consistency
    classification = classification.upper()

    # IFRS 9 staging logic
    if classification in ["C", "SM"]:  # Stage 1 - Performing/Watchlist
        if days_past_due <= 30:
            base_rate = Decimal("0.01")  # 1% - minimal risk
        elif days_past_due <= 60:
            base_rate = Decimal("0.03")  # 3% - increased risk
        else:
            base_rate = Decimal("0.05")  # 5% - high risk within Stage 1

    elif classification in ["SS", "D"]:  # Stage 2 - Substandard/Doubtful
        if days_past_due <= 60:
            base_rate = Decimal("0.20")  # 20% - significant risk
        elif days_past_due <= 90:
            base_rate = Decimal("0.35")  # 35% - very high risk
        else:
            base_rate = Decimal("0.50")  # 50% - approaching Stage 3

    elif classification == "L":  # Stage 3 - Loss
        base_rate = Decimal("1.00")  # 100% - expected loss

    else:
        # Default to 0% for unknown classifications
        base_rate = Decimal("0.00")

    # Add small incremental factor for days past due within each stage
    days_factor = min(days_past_due % 30, 29) / 1000  # Max ~3% additional
    total_rate = base_rate + Decimal(str(days_factor))

    # Ensure rate doesn't exceed 100%
    return min(total_rate, Decimal("1.00"))


def update_ecl_provision(exposure, delinquency):
    """
    Update or create ECL provision based on delinquency status.

    Args:
        exposure: Exposure object related to the loan
        delinquency: DelinquencyStatus object containing the updated classification

    Returns:
        ECLProvisionHistory: The created or updated ECL provision record
    """

    # Calculate provision rate based on classification
    provision_rate = _get_provision_rate_for_classification(
        delinquency.classification, delinquency.days_past_due
    )

    # Calculate provision amount based on outstanding principal only
    principal_outstanding = exposure.principal_outstanding
    provision_amount = principal_outstanding * provision_rate

    # Deactivate any current provisions for this exposure
    ECLProvisionHistory.objects.filter(exposure=exposure, is_current=True).update(
        is_current=False
    )

    # Create new provision record
    ecl_provision = ECLProvisionHistory.objects.create(
        exposure=exposure,
        as_of_date=delinquency.as_of_date,
        provision_rate=provision_rate,
        provision_amount=provision_amount,
        classification=delinquency.classification,
        days_past_due=delinquency.days_past_due,
        method="RULE_BASED",
        remarks=f"Auto-generated provision based on delinquency classification: {delinquency.classification} (calculated against principal outstanding only)",
    )

    return ecl_provision


def update_ecl_provision_for_account(
    account: LoanAccount, as_of_date: Optional[date] = None
) -> None:
    """
    Update ECL provision for all delinquency statuses of a given account.

    Args:
        account: LoanAccount to update provisions for
        as_of_date: Specific date to update (if None, updates all dates)
    """
    from ..models import DelinquencyStatus, Exposure, ECLProvisionHistory

    # Get all delinquency statuses for the account
    delinquencies = DelinquencyStatus.objects.filter(account=account)
    if as_of_date:
        delinquencies = delinquencies.filter(as_of_date=as_of_date)

    for delinquency in delinquencies:
        try:
            # Get corresponding exposure
            exposure = Exposure.objects.get(
                account=account, as_of_date=delinquency.as_of_date
            )

            # Update ECL provision
            update_ecl_provision(exposure, delinquency)

        except Exposure.DoesNotExist:
            # Skip if no corresponding exposure found
            continue
