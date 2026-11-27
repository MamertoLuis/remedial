from django import forms
from .models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
    CollectionActivityLog,
    StrategyAction,
    ECLProvisionHistory,
    Guarantor,
    Collateral,
    StrategyAssessment,
)


LITIGATION_STRATEGY_TYPES = ("Legal Action", "Foreclosure")


class LitigationEntryForm(forms.Form):
    """
    Officer form to raise an account-level litigation entry (target type,
    litigation start date and an officer rationale).
    """

    strategy_type = forms.ChoiceField(
        choices=[(t, t) for t in LITIGATION_STRATEGY_TYPES],
        label="Target Strategy Type",
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Litigation Start Date",
    )
    rationale = forms.CharField(
        widget=forms.Textarea, label="Officer Rationale", help_text="Why is the account entering litigation?"
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
            "borrower_group",
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
            "transaction_type",
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
            "days_past_due",
        ]
        widgets = {
            "as_of_date": forms.DateInput(attrs={"type": "date"}),
        }


class DelinquencyStatusForm(forms.ModelForm):
    class Meta:
        model = DelinquencyStatus
        fields = "__all__"

        widgets = {
            "as_of_date": forms.DateInput(attrs={"type": "date"}),
        }


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
        exclude = ["created_by", "updated_by"]

        widgets = {
            "strategy_start_date": forms.DateInput(attrs={"type": "date"}),
        }


class CollectionActivityLogForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        account = kwargs.pop("account", None)
        super().__init__(*args, **kwargs)
        self.fields["action"].required = False
        if account is not None:
            queryset = StrategyAction.objects.filter(
                strategy__account=account,
                strategy__strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
                status__in=[
                    StrategyAction.ActionStatus.SELECTED,
                    StrategyAction.ActionStatus.APPROVED,
                    StrategyAction.ActionStatus.EXECUTED,
                ],
            )
            # Keep an already-linked action selectable even when its strategy
            # has since exited.
            if self.instance and self.instance.action_id:
                queryset = queryset | StrategyAction.objects.filter(
                    pk=self.instance.action_id
                )
            self.fields["action"].queryset = queryset
        else:
            self.fields["action"].queryset = StrategyAction.objects.none()

    class Meta:
        model = CollectionActivityLog
        fields = [
            "account",
            "action",
            "activity_date",
            "activity_type",
            "promise_to_pay_amount",
            "promise_to_pay_date",
            "staff_assigned",
            "next_action_date",
            "remarks",
        ]
        widgets = {
            "activity_date": forms.DateInput(attrs={"type": "date"}),
            "promise_to_pay_date": forms.DateInput(attrs={"type": "date"}),
            "next_action_date": forms.DateInput(attrs={"type": "date"}),
        }


class RemedialStrategyRecommendationForm(forms.Form):
    """
    Strategy recommendation form: strategy type/date plus the assessment
    snapshot inputs (task 5.1). A recommendation requires an officer
    rationale before the strategy can be created.
    """

    strategy_type = forms.ChoiceField(
        choices=RemedialStrategy.STRATEGY_TYPE_CHOICES, label="Strategy Type"
    )
    strategy_start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Strategy Start Date",
    )
    as_of_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="Assessment As-Of Date"
    )
    officer_rationale = forms.CharField(
        widget=forms.Textarea, label="Officer Rationale"
    )
    financial_condition = forms.ChoiceField(
        choices=StrategyAssessment.FINANCIAL_CONDITION_CHOICES,
        initial="ADEQUATE",
        label="Borrower Financial Condition",
    )
    financial_condition_note = forms.CharField(
        widget=forms.Textarea, required=False, label="Financial Condition Note"
    )
    willingness_to_pay = forms.ChoiceField(
        choices=StrategyAssessment.WILLINGNESS_TO_PAY_CHOICES,
        initial="MEDIUM",
        label="Willingness to Pay",
    )
    willingness_note = forms.CharField(
        widget=forms.Textarea, required=False, label="Willingness Note"
    )
    recovery_outlook = forms.ChoiceField(
        choices=StrategyAssessment.RECOVERY_OUTLOOK_CHOICES,
        initial="MEDIUM",
        label="Recovery Assessment",
    )
    recovery_assessment_note = forms.CharField(
        widget=forms.Textarea, required=False, label="Recovery Assessment Note / Basis"
    )
    expected_recovery = forms.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        label="Expected Recovery",
    )
    guarantors = forms.ModelMultipleChoiceField(
        queryset=Guarantor.objects.none(),
        required=False,
        label="Guarantors",
    )
    collaterals = forms.ModelMultipleChoiceField(
        queryset=Collateral.objects.none(),
        required=False,
        label="Collaterals",
    )

    def __init__(self, *args, account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account
        if account is not None:
            if account.loan_security == "UNSECURED":
                self.fields["strategy_type"].choices = [
                    choice
                    for choice in RemedialStrategy.STRATEGY_TYPE_CHOICES
                    if choice[0] != "Foreclosure"
                ]
            self.fields["guarantors"].queryset = account.guarantors.all()
            self.fields["collaterals"].queryset = account.collaterals.all()

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("officer_rationale"):
            self.add_error(
                "officer_rationale",
                "A strategy recommendation requires an officer rationale.",
            )
        return cleaned

    def assessment_payload(self):
        return {
            "as_of_date": self.cleaned_data.get("as_of_date"),
            "officer_rationale": self.cleaned_data.get("officer_rationale"),
            "financial_condition": self.cleaned_data.get("financial_condition"),
            "financial_condition_note": self.cleaned_data.get(
                "financial_condition_note", ""
            ),
            "willingness_to_pay": self.cleaned_data.get("willingness_to_pay"),
            "willingness_note": self.cleaned_data.get("willingness_note", ""),
            "recovery_outlook": self.cleaned_data.get("recovery_outlook"),
            "recovery_assessment_note": self.cleaned_data.get(
                "recovery_assessment_note", ""
            ),
            "expected_recovery": self.cleaned_data.get("expected_recovery"),
            "guarantors": self.cleaned_data.get("guarantors", []),
            "collaterals": self.cleaned_data.get("collaterals", []),
        }
