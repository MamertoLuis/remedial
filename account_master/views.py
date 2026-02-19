import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .services import *


logger = logging.getLogger(__name__)

from .models import (
    LoanAccount,
    Borrower,
    CollectionActivityLog,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
)
from compromise_agreement.models import CompromiseAgreement
from .forms import (
    LoanAccountForm,
    CollectionActivityLogForm,
    BorrowerForm,
    ExposureForm,
    DelinquencyStatusForm,
    RemedialStrategyForm,
)
from .tables import (
    LoanAccountTable,
    CollectionActivityLogTable,
    BorrowerAccountTable,
    BorrowerTable,
    DashboardCollectionActivityTable,
    ExposureTable,
    DelinquencyStatusTable,
    RemedialStrategyTable,
)
from compromise_agreement.tables import CompromiseAgreementTable
import django_tables2 as tables


def account_list(request):
    accounts = LoanAccount.objects.all()

    account_officer = request.GET.get("account_officer")
    if account_officer and account_officer != "":
        accounts = accounts.filter(account_officer_id=account_officer)
    elif request.user.is_authenticated and request.user.username:
        accounts = accounts.filter(account_officer_id=request.user.username)

    table = LoanAccountTable(accounts)

    account_officers = (
        LoanAccount.objects.exclude(account_officer_id="")
        .values_list("account_officer_id", flat=True)
        .distinct()
        .order_by("account_officer_id")
    )

    return render(
        request,
        "account_master/account_list.html",
        {
            "table": table,
            "account_officers": account_officers,
            "selected_officer": account_officer,
        },
    )


def create_account(request):
    if request.method == "POST":
        form = LoanAccountForm(request.POST)
        if form.is_valid():
            account_data = form.cleaned_data
            upsert_loan_account(loan_id=account_data["loan_id"], defaults=account_data)
            return redirect("account_list")
    else:
        form = LoanAccountForm()
    return render(request, "account_master/create_account.html", {"form": form})


@login_required
def account_detail(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)

    # Summary Cards Data
    latest_exposure = account.exposures.order_by("-as_of_date").first()
    latest_delinquency = account.delinquency_statuses.order_by("-as_of_date").first()
    current_strategy = (
        account.remedial_strategies.filter(strategy_status="ACTIVE")
        .order_by("-strategy_start_date")
        .first()
    )

    # Historical Tables Data
    historical_exposures_table = ExposureTable(
        account.exposures.order_by("-as_of_date")
    )
    historical_delinquency_table = DelinquencyStatusTable(
        account.delinquency_statuses.order_by("-as_of_date")
    )
    historical_strategies_table = RemedialStrategyTable(
        account.remedial_strategies.exclude(strategy_status="ACTIVE").order_by(
            "-strategy_start_date"
        )
    )
    collection_activities_table = CollectionActivityLogTable(
        account.collection_activities.order_by("-activity_date")
    )
    compromise_agreements_table = CompromiseAgreementTable(
        account.compromise_agreements.order_by("-created_at")
    )

    return render(
        request,
        "account_master/account_detail.html",
        {
            "account": account,
            "latest_exposure": latest_exposure,
            "latest_delinquency": latest_delinquency,
            "current_strategy": current_strategy,
            "historical_exposure_table": historical_exposures_table,
            "historical_delinquency_table": historical_delinquency_table,
            "historical_strategies_table": historical_strategies_table,
            "collection_activities_table": collection_activities_table,
            "compromise_agreements_table": compromise_agreements_table,
        },
    )


def update_account(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    if request.method == "POST":
        form = LoanAccountForm(request.POST, instance=account)
        if form.is_valid():
            account_data = form.cleaned_data
            upsert_loan_account(loan_id=loan_id, defaults=account_data)
            return redirect("account_detail", loan_id=loan_id)
    else:
        form = LoanAccountForm(instance=account)
    return render(request, "account_master/update_account.html", {"form": form})


def borrower_list(request):
    borrowers = Borrower.objects.all()
    table = BorrowerTable(borrowers)
    return render(request, "account_master/borrower_list.html", {"table": table})


def borrower_detail(request, borrower_id):
    borrower = get_object_or_404(Borrower, borrower_id=borrower_id)
    accounts = LoanAccount.objects.filter(borrower=borrower)
    table = BorrowerAccountTable(accounts)
    return render(
        request,
        "account_master/borrower_detail.html",
        {"borrower": borrower, "table": table},
    )


def create_borrower(request):
    if request.method == "POST":
        form = BorrowerForm(request.POST)
        if form.is_valid():
            borrower_data = form.cleaned_data
            upsert_borrower(
                borrower_id=borrower_data["borrower_id"], defaults=borrower_data
            )
            return redirect("borrower_list")
    else:
        form = BorrowerForm()
    return render(request, "account_master/create_borrower.html", {"form": form})


def update_borrower(request, borrower_id):
    borrower = get_object_or_404(Borrower, borrower_id=borrower_id)
    if request.method == "POST":
        form = BorrowerForm(request.POST, instance=borrower)
        if form.is_valid():
            borrower_data = form.cleaned_data
            upsert_borrower(borrower_id=borrower_id, defaults=borrower_data)
            return redirect("borrower_detail", borrower_id=borrower.borrower_id)
    else:
        form = BorrowerForm(instance=borrower)
    return render(request, "account_master/update_borrower.html", {"form": form})


def delete_borrower(request, borrower_id):
    borrower = get_object_or_404(Borrower, borrower_id=borrower_id)
    if request.method == "POST":
        borrower.delete()
        return redirect("borrower_list")
    return render(
        request, "account_master/delete_borrower.html", {"borrower": borrower}
    )


def collection_activity_list(request, loan_id):
    account = LoanAccount.objects.get(loan_id=loan_id)
    activities = CollectionActivityLog.objects.filter(account=account).order_by(
        "-activity_date"
    )
    table = CollectionActivityLogTable(activities)
    return render(
        request,
        "account_master/collection_activity_list.html",
        {"account": account, "table": table},
    )


def create_collection_activity(request, loan_id):
    account = LoanAccount.objects.get(loan_id=loan_id)
    if request.method == "POST":
        form = CollectionActivityLogForm(request.POST)
        if form.is_valid():
            activity_data = form.cleaned_data
            create_collection_activity(
                account=account,
                activity_date=activity_data["activity_date"],
                activity_type=activity_data["activity_type"],
                remarks=activity_data["remarks"],
                promise_to_pay_amount=activity_data.get("promise_to_pay_amount"),
                promise_to_pay_date=activity_data.get("promise_to_pay_date"),
                staff_assigned=activity_data.get("staff_assigned"),
                next_action_date=activity_data.get("next_action_date"),
                created_by=request.user,
                updated_by=request.user,
            )
            return redirect("collection_activity_list", loan_id=account.loan_id)
    else:
        form = CollectionActivityLogForm(initial={"account": account})
    return render(
        request,
        "account_master/create_collection_activity.html",
        {"form": form, "account": account},
    )


@login_required
def update_collection_activity(request, loan_id, activity_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    activity = get_object_or_404(
        CollectionActivityLog, activity_id=activity_id, account=account
    )
    if request.method == "POST":
        form = CollectionActivityLogForm(request.POST, instance=activity)
        if form.is_valid():
            activity_data = form.cleaned_data
            create_collection_activity(
                account=account,
                activity_date=activity_data["activity_date"],
                activity_type=activity_data["activity_type"],
                remarks=activity_data["remarks"],
                promise_to_pay_amount=activity_data.get("promise_to_pay_amount"),
                promise_to_pay_date=activity_data.get("promise_to_pay_date"),
                staff_assigned=activity_data.get("staff_assigned"),
                next_action_date=activity_data.get("next_action_date"),
                updated_by=request.user,
            )
            return redirect("collection_activity_list", loan_id=loan_id)
    else:
        form = CollectionActivityLogForm(instance=activity)
    return render(
        request,
        "account_master/update_collection_activity.html",
        {"form": form, "account": account, "activity": activity},
    )


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
def create_delinquency_status(request, loan_id):
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


@login_required
def create_remedial_strategy(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    if request.method == "POST":
        form = RemedialStrategyForm(request.POST)
        if form.is_valid():
            strategy = form.save(commit=False)
            strategy.account = account
            strategy.created_by = request.user
            strategy.updated_by = request.user
            strategy.save()
            return redirect("account_detail", loan_id=loan_id)
    else:
        form = RemedialStrategyForm(initial={"account": account})
    return render(
        request,
        "account_master/create_remedial_strategy.html",
        {"form": form, "account": account},
    )


@login_required
def update_remedial_strategy(request, loan_id, strategy_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    remedial_strategy = get_object_or_404(
        RemedialStrategy, strategy_id=strategy_id, account=account
    )
    if request.method == "POST":
        form = RemedialStrategyForm(request.POST, instance=remedial_strategy)
        if form.is_valid():
            strategy = form.save(commit=False)
            strategy.updated_by = request.user
            strategy.save()
            return redirect("account_detail", loan_id=loan_id)
    else:
        form = RemedialStrategyForm(instance=remedial_strategy)
    return render(
        request,
        "account_master/update_remedial_strategy.html",
        {"form": form, "account": account, "remedial_strategy": remedial_strategy},
    )


def dashboard(request):
    borrower_count = Borrower.objects.count()
    account_count = LoanAccount.objects.count()
    compromise_agreement_count = CompromiseAgreement.objects.count()
    recent_activities = CollectionActivityLog.objects.order_by("-activity_date")[:10]
    activity_table = DashboardCollectionActivityTable(recent_activities)
    context = {
        "borrower_count": borrower_count,
        "account_count": account_count,
        "compromise_agreement_count": compromise_agreement_count,
        "activity_table": activity_table,
    }
    return render(request, "account_master/dashboard.html", context)


def update_account_status(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    if request.method == "POST":
        current_status = account.status
        status_choices = [choice[0] for choice in LoanAccount.LOAN_STATUS_CHOICES]
        try:
            current_index = status_choices.index(current_status)
            next_index = (current_index + 1) % len(status_choices)
            account.status = status_choices[next_index]
            account.save()
        except ValueError:
            # Handle case where current status is not in choices, perhaps set to default
            account.status = status_choices[0]
            account.save()
    return render(request, "account_master/_account_status.html", {"account": account})


@login_required
def remedial_strategy_detail(request, loan_id, strategy_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    strategy = get_object_or_404(
        RemedialStrategy, strategy_id=strategy_id, account=account
    )
    compromise_agreements_table = CompromiseAgreementTable(
        strategy.compromise_agreements.order_by("-created_at")
    )

    context = {
        "account": account,
        "strategy": strategy,
        "compromise_agreements_table": compromise_agreements_table,
    }
    return render(request, "account_master/remedial_strategy_detail.html", context)
