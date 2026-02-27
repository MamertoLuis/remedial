from datetime import date
from decimal import Decimal
from typing import Optional
from django.db import transaction
from ..models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    CollectionActivityLog,
    RemedialStrategy,
    ECLProvisionHistory,
)
from .ecl_service import update_ecl_provision


def upsert_borrower(*, borrower_id: str, defaults: dict) -> tuple[Borrower, bool]:
    """
    Create or update a Borrower.
    """
    borrower_type = defaults.get("borrower_type", "PERSON")
    full_name = defaults.get("full_name")
    primary_address = defaults.get("primary_address")
    mobile = defaults.get("mobile")
    borrower_group = defaults.get("borrower_group")

    obj, created = Borrower.objects.update_or_create(
        borrower_id=borrower_id,
        defaults={
            "borrower_type": borrower_type,
            "full_name": full_name,
            "primary_address": primary_address,
            "mobile": mobile,
            "borrower_group": borrower_group,
        })
    update_fields = {
        "borrower_type": borrower_type,
        "full_name": full_name,
        "primary_address": primary_address,
        "mobile": mobile,
    }
    if "borrower_group" in defaults:
        update_fields["borrower_group"] = borrower_group

    obj, created = Borrower.objects.update_or_create(
        borrower_id=borrower_id,
        defaults=update_fields,
    )
    return obj, created


def upsert_loan_account(*, loan_id: str, defaults: dict) -> tuple[LoanAccount, bool]:
    """
    Create or update a LoanAccount.
    """
    borrower = defaults.get("borrower")
    booking_date = defaults.get("booking_date")
    maturity_date = defaults.get("maturity_date")
    original_principal = defaults.get("original_principal")
    interest_rate = defaults.get("interest_rate")
    loan_type = defaults.get("loan_type")
    account_officer_id = defaults.get("account_officer_id")
    status = defaults.get("status", "PERFORMING")
    loan_security = defaults.get("loan_security", "UNSECURED")

    obj, created = LoanAccount.objects.update_or_create(
        loan_id=loan_id,
        defaults={
            "borrower": borrower,
            "booking_date": booking_date,
            "maturity_date": maturity_date,
            "original_principal": original_principal,
            "interest_rate": interest_rate,
            "loan_type": loan_type,
            "loan_security": loan_security,
            "account_officer_id": account_officer_id,
            "status": status,
        },
    )
    return obj, created


def upsert_exposure(
    *, account: LoanAccount, as_of_date: date, defaults: dict
) -> tuple[Exposure, bool]:
    """
    Create or update an Exposure record.
    Auto-creates DelinquencyStatus from Exposure data.
    """
    principal_outstanding = defaults.get("principal_outstanding", Decimal("0.00"))
    accrued_interest = defaults.get("accrued_interest", Decimal("0.00"))
    accrued_penalty = defaults.get("accrued_penalty", Decimal("0.00"))
    days_past_due = defaults.get("days_past_due", 0)
    snapshot_type = defaults.get("snapshot_type", "EVENT")

    obj, created = Exposure.objects.update_or_create(
        account=account,
        as_of_date=as_of_date,
        defaults={
            "principal_outstanding": principal_outstanding,
            "accrued_interest": accrued_interest,
            "accrued_penalty": accrued_penalty,
            "days_past_due": days_past_due,
            "snapshot_type": snapshot_type,
        },
    )

    _auto_create_delinquency_status(account, as_of_date, days_past_due)

    return obj, created


def _auto_create_delinquency_status(
    account: LoanAccount, as_of_date: date, days_past_due: int
) -> None:
    """
    Auto-create or update DelinquencyStatus from Exposure data.
    Derives classification and aging_bucket based on rules.
    """
    aging_bucket = _derive_aging_bucket(days_past_due)
    classification = _derive_classification(days_past_due)
    npl_flag = classification in ["SS", "D", "L"]

    defaults = {
        "days_past_due": days_past_due,
        "aging_bucket": aging_bucket,
        "classification": classification,
        "npl_flag": npl_flag,
        "snapshot_type": "EVENT",
    }

    DelinquencyStatus.objects.update_or_create(
        account=account,
        as_of_date=as_of_date,
        defaults=defaults,
    )

    _update_loan_account_status(account, classification)


def upsert_delinquency_status(
    *, account: LoanAccount, as_of_date: date, defaults: dict
) -> tuple[DelinquencyStatus, bool]:
    """
    Create or update a DelinquencyStatus record.
    Auto-derives aging_bucket from days_past_due.
    Auto-updates LoanAccount.status based on classification.
    """
    days_past_due = defaults.get("days_past_due", 0)
    aging_bucket = defaults.get("aging_bucket")
    classification = defaults.get("classification", "C")
    npl_flag = defaults.get("npl_flag", False)
    npl_date = defaults.get("npl_date")
    snapshot_type = defaults.get("snapshot_type", "EVENT")

    if aging_bucket is None or aging_bucket == "":
        aging_bucket = _derive_aging_bucket(days_past_due)

    obj, created = DelinquencyStatus.objects.update_or_create(
        account=account,
        as_of_date=as_of_date,
        defaults={
            "days_past_due": days_past_due,
            "aging_bucket": aging_bucket,
            "classification": classification,
            "npl_flag": npl_flag,
            "npl_date": npl_date,
            "snapshot_type": snapshot_type,
        },
    )

    _update_loan_account_status(account, classification)

    return obj, created


def _derive_aging_bucket(days_past_due: int) -> str:
    """
    Derive aging bucket based on days past due.
    """
    if days_past_due == 0:
        return "Current"
    elif 1 <= days_past_due <= 30:
        return "1-30"
    elif 31 <= days_past_due <= 60:
        return "31-60"
    elif 61 <= days_past_due <= 90:
        return "61-90"
    elif 91 <= days_past_due <= 120:
        return "91-120"
    elif 121 <= days_past_due <= 180:
        return "121-180"
    elif 181 <= days_past_due <= 360:
        return "181-360"
    else:
        return "Over 360"


def _derive_classification(days_past_due: int) -> str:
    """
    Derive suggested classification based on days past due.
    This is a suggested value - MANAGER can override.
    """
    if days_past_due == 0:
        return "C"
    elif 1 <= days_past_due <= 90:
        return "SM"
    elif 91 <= days_past_due <= 180:
        return "SS"
    elif 181 <= days_past_due <= 360:
        return "D"
    else:
        return "L"


def _update_loan_account_status(account: LoanAccount, classification: str) -> None:
    """
    Update LoanAccount.status based on delinquency classification.
    """
    latest_exposure = account.exposures.order_by("-as_of_date").first()
    outstanding_balance = (
        latest_exposure.principal_outstanding if latest_exposure else None
    )

    if outstanding_balance == Decimal("1.00"):
        new_status = "WRITEOFF"
    elif outstanding_balance == Decimal("0.00"):
        new_status = "CLOSED"
    elif classification in ["C"]:
        new_status = "PERFORMING"
    elif classification in ["SM"]:
        new_status = "PAST_DUE"
    elif classification in ["SS", "D", "L"]:
        new_status = "NPL"
    else:
        new_status = "PERFORMING"

    if account.status != new_status:
        account.status = new_status
        account.save(update_fields=["status", "updated_at"])


def create_collection_activity(
    *,
    account: LoanAccount,
    activity_date: date,
    activity_type: str,
    remarks: str,
    **kwargs,
) -> CollectionActivityLog:
    """
    Create a new CollectionActivityLog entry.
    """
    return CollectionActivityLog.objects.create(
        account=account,
        activity_date=activity_date,
        activity_type=activity_type,
        remarks=remarks,
        **kwargs,
    )


def create_remedial_strategy(
    *, account: LoanAccount, strategy_type: str, strategy_start_date: date, **kwargs
) -> RemedialStrategy:
    """
    Create a new RemedialStrategy.
    """
    return RemedialStrategy.objects.create(
        account=account,
        strategy_type=strategy_type,
        strategy_start_date=strategy_start_date,
        **kwargs,
    )


@transaction.atomic
def take_snapshot(
    *,
    account: LoanAccount,
    as_of_date: date,
    exposure_data: dict,
    delinquency_data: dict,
) -> None:
    """
    Atomically create or update Exposure and DelinquencyStatus records for a given account and date.
    """
    exposure, _ = upsert_exposure(
        account=account, as_of_date=as_of_date, defaults=exposure_data
    )
    delinquency, _ = upsert_delinquency_status(
        account=account, as_of_date=as_of_date, defaults=delinquency_data
    )

    update_ecl_provision(exposure, delinquency)
