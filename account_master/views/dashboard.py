from django.shortcuts import render
from account_master.models import Borrower, LoanAccount, CollectionActivityLog
from compromise_agreement.models import CompromiseAgreement
from account_master.tables import DashboardCollectionActivityTable


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
