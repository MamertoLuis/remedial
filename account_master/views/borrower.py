from django.shortcuts import render, redirect, get_object_or_404
from account_master.models import Borrower, LoanAccount
from account_master.services import upsert_borrower
from account_master.forms import BorrowerForm
from account_master.tables import BorrowerTable, BorrowerAccountTable
from account_master.filters import BorrowerFilter


def borrower_list(request):
    borrowers = Borrower.objects.all()
    filter = BorrowerFilter(request.GET, queryset=borrowers)
    table = BorrowerTable(filter.qs)
    context = {
        "table": table,
        "filter": filter,
        "breadcrumbs": [
            {"title": "Dashboard", "url": "/"},
            {"title": "Borrowers", "url": None},
        ],
    }
    return render(request, "account_master/borrower_list.html", context)


def borrower_detail(request, borrower_id):
    borrower = get_object_or_404(Borrower, borrower_id=borrower_id)
    accounts = LoanAccount.objects.filter(borrower=borrower)
    table = BorrowerAccountTable(accounts)
    context = {
        "borrower": borrower,
        "table": table,
        "entity_type": "borrower",
        "breadcrumbs": [
            {"title": "Dashboard", "url": ""},
            {"title": "Borrowers", "url": ""},
            {"title": borrower.full_name, "url": None},
        ],
    }
    return render(request, "account_master/borrower_detail.html", context)


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
