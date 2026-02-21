from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from account_master.models import LoanAccount, RemedialStrategy
from account_master.forms import RemedialStrategyForm
from compromise_agreement.tables import CompromiseAgreementTable


@login_required
def create_remedial_strategy(request, loan_id):
    account = get_object_or_404(LoanAccount, loan_id=loan_id)
    if request.method == "POST":
        form = RemedialStrategyForm(request.POST, account=account)
        if form.is_valid():
            strategy = form.save(commit=False)
            strategy.account = account
            strategy.created_by = request.user
            strategy.updated_by = request.user
            strategy.save()
            return redirect("account_detail", loan_id=loan_id)
    else:
        form = RemedialStrategyForm(initial={"account": account}, account=account)
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
    compromise_agreements_table = CompromiseAgreementTable(
        strategy.compromise_agreements.order_by("-created_at")
    )

    context = {
        "account": account,
        "strategy": strategy,
        "compromise_agreements_table": compromise_agreements_table,
    }
    return render(request, "account_master/remedial_strategy_detail.html", context)
