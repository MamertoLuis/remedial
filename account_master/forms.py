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
        fields = "__all__"


class LoanAccountForm(forms.ModelForm):
    class Meta:
        model = LoanAccount
        fields = "__all__"


class ExposureForm(forms.ModelForm):
    class Meta:
        model = Exposure
        fields = "__all__"


class DelinquencyStatusForm(forms.ModelForm):
    class Meta:
        model = DelinquencyStatus
        fields = "__all__"


class RemedialStrategyForm(forms.ModelForm):
    class Meta:
        model = RemedialStrategy
        fields = "__all__"


class CollectionActivityLogForm(forms.ModelForm):
    class Meta:
        model = CollectionActivityLog
        fields = "__all__"
