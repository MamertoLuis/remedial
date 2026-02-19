from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from account_master.models import ECLProvisionHistory, Exposure


def compute_provision_amount(
    total_exposure: Decimal, provision_rate: Decimal
) -> Decimal:
    total_exposure = total_exposure or Decimal("0")
    provision_rate = provision_rate or Decimal("0")

    # Round to cents
    return (total_exposure * provision_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


@transaction.atomic
def create_provision_entry(
    *,
    exposure: Exposure,
    provision_rate: Decimal,
    method: str = "RULE_BASED",
    remarks: str = "",
    classification: str | None = None,
    days_past_due: int | None = None,
    user=None,
):
    if provision_rate is None:
        raise ValueError("Provision rate is required.")

    if provision_rate < 0:
        raise ValueError("Provision rate cannot be negative.")

    # Deactivate old current record
    ECLProvisionHistory.objects.filter(exposure=exposure, is_current=True).update(
        is_current=False
    )

    provision_amount = compute_provision_amount(exposure.total_exposure, provision_rate)

    entry = ECLProvisionHistory.objects.create(
        exposure=exposure,
        as_of_date=exposure.as_of_date,
        provision_rate=provision_rate,
        provision_amount=provision_amount,
        classification=classification,
        days_past_due=days_past_due,
        method=method,
        remarks=remarks,
        is_current=True,
        created_by=user,
        updated_by=user,
    )

    return entry
