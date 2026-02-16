from django.shortcuts import render, redirect
from .models import AccountMaster
from .forms import AccountMasterForm

def account_list(request):
    accounts = AccountMaster.objects.all()
    return render(request, 'account_master/account_list.html', {'accounts': accounts})

def create_account(request):
    if request.method == 'POST':
        form = AccountMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('account_list')
    else:
        form = AccountMasterForm()
    return render(request, 'account_master/create_account.html', {'form': form})

