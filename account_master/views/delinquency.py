import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from account_master.models import LoanAccount, DelinquencyStatus
from account_master.services import upsert_delinquency_status
from account_master.forms import DelinquencyStatusForm

logger = logging.getLogger(__name__)


def _is_manager_or_board_member(user):
    return user.is_authenticated and user.role in ["MANAGER", "BOARD_MEMBER"]


@login_required
def create_delinquency_status(request, loan_id):
    if not _is_manager_or_board_member(request.user):
        return render(request, "account_master/403.html", status=403)

    logger.info(f"create_delinquency_status called for loan_id: {loan_id}")
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    if request.method == "POST":
        form = DelinquencyStatusForm(request.POST)
        if form.is_valid():
            delinquency_data = form.cleaned_data
            upsert_delinquency_status(
                account=account,
                as_of_date=delinquency_data["as_of_date"],
                defaults=delinquency_data,
            )
            return redirect("account_detail", loan_id=loan_id)
        else:
            logger.error(f"DelinquencyStatus form is not valid: {form.errors}")
    else:
        form = DelinquencyStatusForm(initial={"account": account})
    return render(
        request,
        "account_master/create_delinquency_status.html",
        {"form": form, "account": account},
    )


@login_required
def update_delinquency_status(request, loan_id, delinquency_id):
    if not _is_manager_or_board_member(request.user):
        return render(request, "account_master/403.html", status=403)

    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    delinquency_status = get_object_or_404(
        DelinquencyStatus, delinquency_id=delinquency_id, account=account
    )
    if request.method == "POST":
        form = DelinquencyStatusForm(request.POST, instance=delinquency_status)
        if form.is_valid():
            delinquency_data = form.cleaned_data
            upsert_delinquency_status(
                account=account,
                as_of_date=delinquency_data["as_of_date"],
                defaults=delinquency_data,
            )
            return redirect("account_detail", loan_id=loan_id)
    else:
        form = DelinquencyStatusForm(instance=delinquency_status)
    return render(
        request,
        "account_master/update_delinquency_status.html",
        {"form": form, "account": account, "delinquency_status": delinquency_status},
    )
