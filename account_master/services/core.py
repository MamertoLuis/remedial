from datetime import date
from decimal import Decimal
from django.db import transaction
from ..models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    CollectionActivityLog,
    RemedialStrategy,
)


def upsert_borrower(*, borrower_id: str, defaults: dict) -> tuple[Borrower, bool]:
    """
    Create or update a Borrower.
    """
    borrower_type = defaults.get("borrower_type", "PERSON")
    full_name = defaults.get("full_name")
    tin = defaults.get("tin")
    birth_or_incorp_date = defaults.get("birth_or_incorp_date")
    primary_address = defaults.get("primary_address")
    mobile = defaults.get("mobile")
    email = defaults.get("email")
    risk_rating = defaults.get("risk_rating")

    obj, created = Borrower.objects.update_or_create(
        borrower_id=borrower_id,
        defaults={
            "borrower_type": borrower_type,
            "full_name": full_name,
            "tin": tin,
            "birth_or_incorp_date": birth_or_incorp_date,
            "primary_address": primary_address,
            "mobile": mobile,
            "email": email,
            "risk_rating": risk_rating,
        },
    )
    return obj, created


def upsert_loan_account(*, loan_id: str, defaults: dict) -> tuple[LoanAccount, bool]:
    """
    Create or update a LoanAccount.
    """
    borrower = defaults.get("borrower")
    pn_number = defaults.get("pn_number")
    booking_date = defaults.get("booking_date")
    maturity_date = defaults.get("maturity_date")
    original_principal = defaults.get("original_principal")
    interest_rate = defaults.get("interest_rate")
    loan_type = defaults.get("loan_type")
    branch_code = defaults.get("branch_code")
    account_officer_id = defaults.get("account_officer_id")
    status = defaults.get("status", "PERFORMING")

    obj, created = LoanAccount.objects.update_or_create(
        loan_id=loan_id,
        defaults={
            "borrower": borrower,
            "pn_number": pn_number,
            "booking_date": booking_date,
            "maturity_date": maturity_date,
            "original_principal": original_principal,
            "interest_rate": interest_rate,
            "loan_type": loan_type,
            "branch_code": branch_code,
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
    """
    principal_outstanding = defaults.get("principal_outstanding", Decimal("0.00"))
    accrued_interest = defaults.get("accrued_interest", Decimal("0.00"))
    accrued_penalty = defaults.get("accrued_penalty", Decimal("0.00"))
    legal_fees = defaults.get("legal_fees", Decimal("0.00"))
    other_charges = defaults.get("other_charges", Decimal("0.00"))
    provision_rate = defaults.get("provision_rate", Decimal("0.00"))
    snapshot_type = defaults.get("snapshot_type", "EVENT")

    total_exposure = (
        principal_outstanding
        + accrued_interest
        + accrued_penalty
        + legal_fees
        + other_charges
    )
    provision_amount = total_exposure * provision_rate

    obj, created = Exposure.objects.update_or_create(
        account=account,
        as_of_date=as_of_date,
        defaults={
            "principal_outstanding": principal_outstanding,
            "accrued_interest": accrued_interest,
            "accrued_penalty": accrued_penalty,
            "legal_fees": legal_fees,
            "other_charges": other_charges,
            "total_exposure": total_exposure,
            "provision_rate": provision_rate,
            "provision_amount": provision_amount,
            "snapshot_type": snapshot_type,
        },
    )
    return obj, created


def upsert_delinquency_status(
    *, account: LoanAccount, as_of_date: date, defaults: dict
) -> tuple[DelinquencyStatus, bool]:
    """
    Create or update a DelinquencyStatus record.
    """
    days_past_due = defaults.get("days_past_due", 0)
    aging_bucket = defaults.get("aging_bucket")
    classification = defaults.get("classification", "C")
    npl_flag = defaults.get("npl_flag", False)
    npl_date = defaults.get("npl_date")
    snapshot_type = defaults.get("snapshot_type", "EVENT")

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
    return obj, created


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
    upsert_exposure(account=account, as_of_date=as_of_date, defaults=exposure_data)
    upsert_delinquency_status(
        account=account, as_of_date=as_of_date, defaults=delinquency_data
    )
