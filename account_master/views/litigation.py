from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from account_master.forms import LitigationEntryForm
from account_master.models import LitigationEntry, LoanAccount
from account_master.services import litigation_service
from account_master.decorators import manager_required, officer_required


def _ladder_redirect(loan_id):
    return redirect("escalation_ladder_detail", loan_id=loan_id)


@officer_required
def raise_litigation_entry(request, loan_id):
    """Officer-facing flow to record that an account is entering litigation."""
    account = get_object_or_404(LoanAccount, loan_id=loan_id)

    if request.method == "POST":
        form = LitigationEntryForm(request.POST)
        if form.is_valid():
            try:
                entry = litigation_service.raise_litigation_entry(
                    account=account,
                    strategy_type=form.cleaned_data["strategy_type"],
                    start_date=form.cleaned_data["start_date"],
                    rationale=form.cleaned_data["rationale"],
                    officer=request.user,
                )
                messages.success(
                    request,
                    "Litigation entry raised and is pending manager approval.",
                )
                return _ladder_redirect(loan_id)
            except ValidationError as exc:
                form.add_error(None, exc)
    else:
        form = LitigationEntryForm()

    context = {
        "account": account,
        "form": form,
        "cancel_url": reverse("escalation_ladder_detail", args=[loan_id]),
        "active_entry": litigation_service.get_active_entry(account),
        "breadcrumbs": [
            {"title": "Account", "url": "account_detail"},
            {"title": "Escalation Ladder", "url": "escalation_ladder_detail"},
            {"title": f"Raise Litigation Entry - {account.loan_id}", "url": None},
        ],
    }
    return render(
        request,
        "account_master/raise_litigation_entry.html",
        context,
    )


@manager_required
def litigation_entry_queue(request):
    """Manager-facing queue of pending litigation entries awaiting decision."""
    pending = litigation_service.get_pending_entries().select_related(
        "account", "raised_by"
    )
    context = {
        "pending_entries": pending,
        "breadcrumbs": [
            {"title": "Strategy Approval Queue", "url": "approval_queue"},
            {"title": "Litigation Entries", "url": None},
        ],
    }
    return render(
        request,
        "account_master/litigation_entry_queue.html",
        context,
    )


@manager_required
def decide_litigation_entry(request, litigation_id):
    """Manager-facing approve / reject action on a pending litigation entry."""
    entry = get_object_or_404(LitigationEntry, litigation_id=litigation_id)

    if request.method == "POST":
        decision = request.POST.get("decision")
        notes = request.POST.get("decision_notes", "")
        try:
            if decision == "APPROVE":
                litigation_service.approve_litigation_entry(
                    entry, approver=request.user, notes=notes
                )
                messages.success(request, "Litigation entry approved.")
            elif decision == "REJECT":
                litigation_service.reject_litigation_entry(
                    entry, approver=request.user, notes=notes
                )
                messages.success(request, "Litigation entry rejected.")
            else:
                messages.error(request, "Unknown decision.")
                return redirect(reverse("approval_queue") + "?tab=litigation")
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))
            return redirect(reverse("approval_queue") + "?tab=litigation")
        return redirect("approval_queue")

    context = {
        "entry": entry,
        "account": entry.account,
        "breadcrumbs": [
            {"title": "Litigation Entries", "url": "litigation_entry_queue"},
            {"title": f"Decision - {entry.account.loan_id}", "url": None},
        ],
    }
    return render(
        request,
        "account_master/decide_litigation_entry.html",
        context,
    )