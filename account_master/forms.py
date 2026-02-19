from django import forms
from .models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
    CollectionActivityLog,
    ECLProvisionHistory,
)


class ECLProvisionHistoryForm(forms.ModelForm):
    class Meta:
        model = ECLProvisionHistory
        fields = "__all__"
        widgets = {
            "as_of_date": forms.DateInput(attrs={"type": "date"}),
        }


# Stub forms for existing views - not used in API
class BorrowerForm(forms.ModelForm):
    class Meta:
        model = Borrower
        fields = [
            "borrower_id",
            "borrower_type",
            "full_name",
            "primary_address",
            "mobile",
        ]


class LoanAccountForm(forms.ModelForm):
    class Meta:
        model = LoanAccount
        fields = [
            "loan_id",
            "borrower",
            "booking_date",
            "maturity_date",
            "original_principal",
            "interest_rate",
            "loan_type",
            "loan_security",
            "account_officer_id",
            "status",
        ]
        widgets = {
            "booking_date": forms.DateInput(attrs={"type": "date"}),
            "maturity_date": forms.DateInput(attrs={"type": "date"}),
        }


class ExposureForm(forms.ModelForm):
    class Meta:
        model = Exposure
        fields = [
            "exposure_id",
            "account",
            "as_of_date",
            "snapshot_type",
            "principal_outstanding",
            "accrued_interest",
            "accrued_penalty",
            "total_exposure",
        ]
        widgets = {
            "as_of_date": forms.DateInput(attrs={"type": "date"}),
        }


class DelinquencyStatusForm(forms.ModelForm):
    class Meta:
        model = DelinquencyStatus
        fields = "__all__"


class RemedialStrategyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        account = kwargs.pop("account", None)
        super().__init__(*args, **kwargs)

        if account:
            # Filter out Foreclosure option for unsecured loans
            if account.loan_security == "UNSECURED":
                self.fields["strategy_type"].choices = [
                    choice
                    for choice in RemedialStrategy.STRATEGY_TYPE_CHOICES
                    if choice[0] != "Foreclosure"
                ]

    class Meta:
        model = RemedialStrategy
        fields = "__all__"


class CollectionActivityLogForm(forms.ModelForm):
    class Meta:
        model = CollectionActivityLog
        fields = "__all__"
