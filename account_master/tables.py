import django_tables2 as tables
from .models import AccountMaster


class AccountMasterTable(tables.Table):
    account_id = tables.LinkColumn('account_detail', args=[tables.A('account_id')])

    class Meta:
        model = AccountMaster
        fields = ('account_id', 'borrower', 'loan_type', 'current_status')
        attrs = {'class': 'table table-striped'}
