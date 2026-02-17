from django import forms
from .models import CompromiseAgreement, CompromiseInstallment

class CompromiseAgreementForm(forms.ModelForm):
    class Meta:
        model = CompromiseAgreement
        fields = [
            'account',
            'original_total_exposure',
            'approved_compromise_amount',
            'approval_level',
            'approval_date',
            'installment_flag',
            'rescission_clause_flag',
            'status',
        ]
        widgets = {
            'approval_date': forms.DateInput(attrs={'type': 'date'}),
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
