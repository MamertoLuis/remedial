from django.shortcuts import render, redirect
from .models import AccountMaster, Borrower
from .forms import AccountMasterForm
from .tables import AccountMasterTable
import django_tables2 as tables

def account_list(request):
    accounts = AccountMaster.objects.all()
    table = AccountMasterTable(accounts)
    return render(request, 'account_master/account_list.html', {'table': table})

def create_account(request):
    if request.method == 'POST':
        form = AccountMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('account_list')
    else:
        form = AccountMasterForm()
    return render(request, 'account_master/create_account.html', {'form': form})

def account_detail(request, account_id):
    account = AccountMaster.objects.get(account_id=account_id)
    return render(request, 'account_master/account_detail.html', {'account': account})

def update_account(request, account_id):
    account = AccountMaster.objects.get(account_id=account_id)
    if request.method == 'POST':
        form = AccountMasterForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            return redirect('account_detail', account_id=account_id)
    else:
        form = AccountMasterForm(instance=account)
    return render(request, 'account_master/update_account.html', {'form': form})

def borrower_detail(request, borrower_id):
    borrower = Borrower.objects.get(borrower_id=borrower_id)
    accounts = AccountMaster.objects.filter(borrower=borrower)
    return render(request, 'account_master/borrower_detail.html', {
        'borrower': borrower,
        'accounts': accounts
    })


