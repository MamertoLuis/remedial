import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from account_master.models import LoanAccount, Exposure
from account_master.services import upsert_exposure
from account_master.forms import ExposureForm

logger = logging.getLogger(__name__)


@login_required
def create_exposure(request, loan_id):
    logger.info(f"create_exposure called for loan_id: {loan_id}")
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    if request.method == "POST":
        form = ExposureForm(request.POST)
        if form.is_valid():
            exposure_data = form.cleaned_data
            upsert_exposure(
                account=account,
                as_of_date=exposure_data["as_of_date"],
                defaults=exposure_data,
            )
            return redirect("account_detail", loan_id=loan_id)
        else:
            logger.error(f"Exposure form is not valid: {form.errors}")
    else:
        form = ExposureForm(initial={"account": account})
    return render(
        request,
        "account_master/create_exposure.html",
        {"form": form, "account": account},
    )


@login_required
def update_exposure(request, loan_id, exposure_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    exposure = get_object_or_404(Exposure, exposure_id=exposure_id, account=account)
    if request.method == "POST":
        form = ExposureForm(request.POST, instance=exposure)
        if form.is_valid():
            exposure_data = form.cleaned_data
            upsert_exposure(
                account=account,
                as_of_date=exposure_data["as_of_date"],
                defaults=exposure_data,
            )
            return redirect("account_detail", loan_id=loan_id)
    else:
        form = ExposureForm(instance=exposure)
    return render(
        request,
        "account_master/update_exposure.html",
        {"form": form, "account": account, "exposure": exposure},
    )

@login_required
def exposure_list(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    exposures = Exposure.objects.filter(account=account).order_by("-as_of_date")
    return render(
        request,
        "account_master/exposure_list.html",
        {"account": account, "exposures": exposures},
    )
