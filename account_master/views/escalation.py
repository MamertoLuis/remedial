from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from account_master.models import LoanAccount, Notice
from account_master.services.escalation_service import (
    get_open_state,
    issue_notice,
)


@login_required
def escalation_ladder_detail(request, loan_id):
    """Officer-facing ladder view: current stage/status, next notice due and
    the account's notice history."""
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    escalation_state = get_open_state(account)
    notices = (
        account.notices.select_related("stage", "issued_by").order_by("-issued_on")[:50]
    )

    context = {
        "account": account,
        "escalation_state": escalation_state,
        "notices": notices,
        "breadcrumbs": [
            {"title": "Dashboard", "url": ""},
            {"title": "Loan Accounts", "url": ""},
            {"title": f"Escalation Ladder - {account.loan_id}", "url": None},
        ],
    }
    return render(request, "account_master/escalation_ladder.html", context)


@login_required
def issue_escalation_notice(request, loan_id):
    """Issue a notice for the account's current escalation stage."""
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    escalation_state = get_open_state(account)

    if request.method == "POST":
        if escalation_state is not None:
            method = request.POST.get("method")
            if method:
                issue_notice(
                    account,
                    escalation_state.current_stage,
                    method,
                    user=request.user,
                )
        return redirect("escalation_ladder_detail", loan_id=loan_id)

    context = {
        "account": account,
        "escalation_state": escalation_state,
        "methods": Notice.Method.choices,
        "breadcrumbs": [
            {"title": "Dashboard", "url": ""},
            {"title": "Loan Accounts", "url": ""},
            {"title": f"Issue Notice - {account.loan_id}", "url": None},
        ],
    }
    return render(request, "account_master/issue_notice.html", context)
