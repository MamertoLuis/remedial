from django import forms
from .models import AccountMaster

class AccountMasterForm(forms.ModelForm):
    class Meta:
        model = AccountMaster
        fields = '__all__'
