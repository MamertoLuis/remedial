from django import forms
from .models import CompromiseAgreement, CompromiseInstallment
from account_master.models import RemedialStrategy

class CompromiseAgreementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['strategy'].disabled = True
        self.fields['account'].disabled = True

    class Meta:
        model = CompromiseAgreement
        fields = [
            'strategy',
            'account',
            'original_total_exposure',
            'approved_compromise_amount',
            'approval_level',
            'approval_date',
            'installment_flag',
            'number_of_installments',
            'payment_frequency',
            'first_payment_date',
            'rescission_clause_flag',
            'status',
        ]
        widgets = {
            'approval_date': forms.DateInput(attrs={'type': 'date'}),
            'first_payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

class CompromiseInstallmentForm(forms.ModelForm):
    class Meta:
        model = CompromiseInstallment
        fields = [
            'compromise_agreement',
            'installment_number',
            'due_date',
            'amount_due',
            'amount_paid',
            'payment_date',
            'status',
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }
