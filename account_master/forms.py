from django import forms
from .models import AccountMaster, Borrower

class AccountMasterForm(forms.ModelForm):
    class Meta:
        model = AccountMaster
        fields = '__all__'

class BorrowerForm(forms.ModelForm):
    class Meta:
        model = Borrower
        fields = '__all__'

