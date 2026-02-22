from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from django.db.models import OuterRef, Subquery
from account_master.models import (
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
    CollectionActivityLog,
    ECLProvisionHistory,
)
from account_master.services import upsert_loan_account
from account_master.forms import LoanAccountForm
from account_master.tables import (
    LoanAccountTable,
    ExposureTable,
    DelinquencyStatusTable,
    RemedialStrategyTable,
    CollectionActivityLogTable,
)
from compromise_agreement.tables import CompromiseAgreementTable


def account_list(request):
    latest_exposure = Exposure.objects.filter(account=OuterRef("pk")).order_by(
        "-as_of_date"
    )

    accounts = LoanAccount.objects.annotate(
        outstanding_balance=Subquery(
            latest_exposure.values("principal_outstanding")[:1]
        )
    )

    account_officer = request.GET.get("account_officer")
    if account_officer and account_officer != "":
        accounts = accounts.filter(account_officer_id=account_officer)

    status = request.GET.get("status")
    if status and status != "":
        accounts = accounts.filter(status=status)

    security = request.GET.get("security")
    if security and security != "":
        accounts = accounts.filter(loan_security=security)

    table = LoanAccountTable(accounts, user=request.user)

    account_officers = (
        LoanAccount.objects.exclude(account_officer_id="")
        .values_list("account_officer_id", flat=True)
        .distinct()
        .order_by("account_officer_id")
    )

    context = {
        "table": table,
        "account_officers": account_officers,
        "selected_officer": account_officer,
        "selected_status": status,
        "selected_security": security,
        "status_choices": LoanAccount.LOAN_STATUS_CHOICES,
        "security_choices": LoanAccount.LOAN_SECURITY_CHOICES,
        "breadcrumbs": [
            {"title": "Dashboard", "url": "/"},
            {"title": "Loan Accounts", "url": None},
        ],
    }

    return render(request, "account_master/account_list.html", context)


def create_account(request, borrower_id=None):
    from account_master.models import Borrower

    if borrower_id:
        borrower = get_object_or_404(Borrower, borrower_id=borrower_id)
        initial = {"borrower": borrower}
    else:
        initial = {}

    if request.method == "POST":
        form = LoanAccountForm(request.POST)
        if form.is_valid():
            account_data = form.cleaned_data
            upsert_loan_account(loan_id=account_data["loan_id"], defaults=account_data)
            if borrower_id:
                return redirect("borrower_detail", borrower_id=borrower_id)
            return redirect("account_list")
    else:
        form = LoanAccountForm(initial=initial)
    return render(request, "account_master/create_account.html", {"form": form})


def account_detail(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)

    latest_exposure = account.exposures.order_by("-as_of_date").first()
    latest_delinquency = account.delinquency_statuses.order_by("-as_of_date").first()
    current_strategy = (
        account.remedial_strategies.filter(strategy_status="ACTIVE")
        .order_by("-strategy_start_date")
        .first()
    )

    # Get latest ECL provision
    latest_ecl_provision = None
    if latest_exposure:
        latest_ecl_provision = ECLProvisionHistory.objects.filter(
            exposure=latest_exposure, is_current=True
        ).first()

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

    # Calculate formatted ECL provision rate if available
    formatted_provision_rate = None
    if latest_ecl_provision:
        formatted_provision_rate = latest_ecl_provision.provision_rate * 100

    context = {
        "account": account,
        "latest_exposure": latest_exposure,
        "latest_delinquency": latest_delinquency,
        "current_strategy": current_strategy,
        "latest_ecl_provision": latest_ecl_provision,
        "formatted_provision_rate": formatted_provision_rate,
        "historical_exposure_table": historical_exposures_table,
        "historical_delinquency_table": historical_delinquency_table,
        "historical_strategies_table": historical_strategies_table,
        "collection_activities_table": collection_activities_table,
        "compromise_agreements_table": compromise_agreements_table,
        "entity_type": "loan",
        "breadcrumbs": [
            {"title": "Dashboard", "url": ""},
            {"title": "Loan Accounts", "url": ""},
            {"title": f"Loan {account.loan_id}", "url": None},
        ],
    }

    return render(request, "account_master/account_detail.html", context)


@csrf_exempt
def generate_ecl_provision(request, loan_id):
    """
    Generate ECL provision for a loan account based on latest exposure and delinquency data.
    Returns JSON response for AJAX calls.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST request required"})

    try:
        account = get_object_or_404(LoanAccount, loan_id=loan_id)

        # Get latest exposure and delinquency
        latest_exposure = account.exposures.order_by("-as_of_date").first()
        latest_delinquency = account.delinquency_statuses.order_by(
            "-as_of_date"
        ).first()

        if not latest_exposure:
            return JsonResponse({"success": False, "error": "No exposure data found"})

        if not latest_delinquency:
            return JsonResponse(
                {"success": False, "error": "No delinquency data found"}
            )

        # Import the ECL service function
        from account_master.services.ecl_service import update_ecl_provision

        # Generate ECL provision
        ecl_provision = update_ecl_provision(latest_exposure, latest_delinquency)

        return JsonResponse(
            {
                "success": True,
                "provision_amount": float(ecl_provision.provision_amount),
                "provision_rate": float(ecl_provision.provision_rate),
                "classification": ecl_provision.classification,
                "as_of_date": ecl_provision.as_of_date.isoformat(),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


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
            account.status = status_choices[0]
            account.save()
    return render(request, "account_master/_account_status.html", {"account": account})
