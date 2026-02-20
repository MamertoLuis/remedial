from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from account_master.models import LoanAccount, CollectionActivityLog
from account_master.services import create_collection_activity
from account_master.forms import CollectionActivityLogForm
from account_master.tables import CollectionActivityLogTable


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
