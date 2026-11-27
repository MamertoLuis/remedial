from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django_tables2 import RequestConfig

from account_master.forms import RemedialStrategyForm, RemedialStrategyRecommendationForm
from account_master.models import LoanAccount, RemedialStrategy, StrategyApproval
from account_master.services import litigation_service, strategy_service
from account_master.decorators import manager_required
from compromise_agreement.tables import CompromiseAgreementTable


def _deny_board_mutations(request):
    """BOARD_MEMBER is read-only on strategy pages (spec 5.4)."""
    if request.user.role == "BOARD_MEMBER":
        return True
    return False


@login_required
def create_remedial_strategy(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    if request.method == "POST":
        form = RemedialStrategyRecommendationForm(request.POST, account=account)
        if form.is_valid():
            try:
                strategy = strategy_service.create_strategy_recommendation(
                    account=account,
                    strategy_type=form.cleaned_data["strategy_type"],
                    strategy_start_date=form.cleaned_data["strategy_start_date"],
                    officer=request.user,
                    assessment=form.assessment_payload(),
                )
                messages.success(request, "Strategy recommended and activated.")
                return redirect("account_detail", loan_id=loan_id)
            except ValidationError as exc:
                form.add_error(None, exc)
    else:
        initial = {
            "as_of_date": timezone.now().date(),
            "strategy_start_date": timezone.now().date(),
        }
        form = RemedialStrategyRecommendationForm(initial=initial, account=account)
    return render(
        request,
        "account_master/create_remedial_strategy.html",
        {"form": form, "account": account, "is_recommendation": True},
    )


@login_required
def update_remedial_strategy(request, loan_id, strategy_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    remedial_strategy = get_object_or_404(
        RemedialStrategy, strategy_id=strategy_id, account=account
    )
    if request.method == "POST":
        form = RemedialStrategyForm(
            request.POST, instance=remedial_strategy, account=account
        )
        if form.is_valid():
            strategy = form.save(commit=False)
            strategy.updated_by = request.user
            strategy.save()
            return redirect("account_detail", loan_id=loan_id)
    else:
        form = RemedialStrategyForm(instance=remedial_strategy, account=account)
    return render(
        request,
        "account_master/update_remedial_strategy.html",
        {"form": form, "account": account, "remedial_strategy": remedial_strategy},
    )


@login_required
def remedial_strategy_detail(request, loan_id, strategy_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    strategy = get_object_or_404(
        RemedialStrategy, strategy_id=strategy_id, account=account
    )

    if request.method == "POST":
        try:
            _handle_strategy_post(request, strategy)
            messages.success(request, "Action updated.")
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))
        except Exception as exc:  # noqa: BLE001 - surface any form error to the officer
            messages.error(request, f"Unable to update: {exc}")
        return redirect("remedial_strategy_detail", loan_id=loan_id, strategy_id=strategy_id)

    compromise_agreements_table = CompromiseAgreementTable(
        strategy.compromise_agreements.order_by("-created_at")
    )
    RequestConfig(request).configure(compromise_agreements_table)
    compromise_agreements_table.paginate(page=request.GET.get("page", 1), per_page=25)

    context = {
        "account": account,
        "strategy": strategy,
        "compromise_agreements_table": compromise_agreements_table,
        "assessment": getattr(strategy, "assessment", None),
        "catalog": strategy_service.get_action_catalog(strategy),
        "actions": strategy.actions.select_related("catalog_entry").order_by(
            "action_id"
        ),
        "approvals": StrategyApproval.objects.filter(
            action__strategy=strategy
        ).select_related("action__catalog_entry", "approver"),
        "is_board_member": request.user.role == "BOARD_MEMBER",
        "is_manager": request.user.role == "MANAGER",
    }
    return render(request, "account_master/remedial_strategy_detail.html", context)


def _handle_strategy_post(request, strategy):
    """Process action selection / execution / failure-declaration POSTs."""
    action_kind = request.POST.get("action")
    if action_kind == "select":
        if _deny_board_mutations(request):
            raise ValidationError("Board members have read-only access.")
        entry_id = request.POST.get("catalog_entry_id")
        strategy_service.select_action(
            strategy=strategy,
            catalog_entry=int(entry_id),
            assignee=request.POST.get("assignee", ""),
            due_date=request.POST.get("due_date") or None,
            officer=request.user,
        )
    elif action_kind == "execute":
        if _deny_board_mutations(request):
            raise ValidationError("Board members have read-only access.")
        action = strategy.actions.filter(
            action_id=request.POST.get("action_id")
        ).first()
        if action is None:
            raise ValidationError("Unknown action.")
        strategy_service.execute_action(
            action=action,
            outcome=request.POST.get("outcome", ""),
            assignee=request.POST.get("assignee") or None,
            executed_on=request.POST.get("executed_on") or None,
            officer=request.user,
        )
    elif action_kind == "log_execute":
        if _deny_board_mutations(request):
            raise ValidationError("Board members have read-only access.")
        action = strategy.actions.filter(
            action_id=request.POST.get("action_id")
        ).first()
        if action is None:
            raise ValidationError("Unknown action.")
        strategy_service.execute_action_and_log_activity(
            action=action,
            outcome=request.POST.get("outcome", ""),
            activity_type=request.POST.get("activity_type", ""),
            remarks=request.POST.get("remarks", ""),
            executed_on=request.POST.get("executed_on") or None,
            officer=request.user,
        )
    elif action_kind == "update":
        if _deny_board_mutations(request):
            raise ValidationError("Board members have read-only access.")
        action = strategy.actions.filter(
            action_id=request.POST.get("action_id")
        ).first()
        if action is None:
            raise ValidationError("Unknown action.")
        strategy_service.update_action_planning(
            action=action,
            assignee=request.POST.get("assignee", ""),
            due_date=request.POST.get("due_date") or None,
            officer=request.user,
        )
    elif action_kind == "skip":
        if _deny_board_mutations(request):
            raise ValidationError("Board members have read-only access.")
        action = strategy.actions.filter(
            action_id=request.POST.get("action_id")
        ).first()
        if action is None:
            raise ValidationError("Unknown action.")
        strategy_service.skip_action(
            action=action,
            outcome=request.POST.get("outcome", ""),
            officer=request.user,
        )
    elif action_kind == "fail":
        if _deny_board_mutations(request):
            raise ValidationError("Board members have read-only access.")
        strategy_service.declare_failure(
            strategy=strategy,
            officer=request.user,
            outcome=request.POST.get("outcome", ""),
            unmet_conditions_note=request.POST.get("unmet_conditions_note", ""),
        )
    else:
        raise ValidationError("Unknown action.")


@manager_required
def approval_queue(request):
    """Manager-only approval queue (task 5.3)."""
    if request.method == "POST":
        action_id = request.POST.get("action_id")
        action = strategy_service.list_pending_approvals().filter(
            action_id=action_id
        ).first()
        decision = request.POST.get("decision")
        try:
            if action is None:
                raise ValidationError("Unknown or already-decided action.")
            if decision == "approve":
                strategy_service.approve_action(
                    action=action,
                    approver=request.user,
                    comments=request.POST.get("comments", ""),
                    conditions=request.POST.get("conditions", ""),
                )
                messages.success(request, "Action approved.")
            elif decision == "reject":
                strategy_service.reject_action(
                    action=action,
                    approver=request.user,
                    comments=request.POST.get("comments", ""),
                )
                messages.success(request, "Action rejected.")
            else:
                raise ValidationError("Missing decision.")
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))
        return redirect("approval_queue")

    pending = strategy_service.list_pending_approvals()
    pending_entries = litigation_service.get_pending_entries().select_related(
        "account", "raised_by"
    )
    tab = request.GET.get("tab", "strategy")
    if tab not in ("strategy", "litigation"):
        tab = "strategy"
    return render(
        request,
        "account_master/approval_queue.html",
        {
            "pending_actions": pending,
            "pending_entries": pending_entries,
            "tab": tab,
        },
    )
