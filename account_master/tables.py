import django_tables2 as tables
from .models import (
    LoanAccount,
    CollectionActivityLog,
    Borrower,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
)


class BorrowerTable(tables.Table):
    borrower_id = tables.LinkColumn("borrower_detail", args=[tables.A("borrower_id")])

    class Meta:
        model = Borrower
        fields = (
            "borrower_id",
            "full_name",
            "borrower_type",
            "mobile",
            "borrower_group",
        )
        attrs = {"class": "table table-striped"}


class LoanAccountTable(tables.Table):
    loan_id = tables.LinkColumn("account_detail", args=[tables.A("loan_id")])
    borrower = tables.Column(
        accessor="borrower.full_name", order_by="borrower__full_name"
    )
    account_officer_id = tables.Column()
    outstanding_balance = tables.Column(
        verbose_name="Outstanding Balance", order_by="outstanding_balance"
    )

    class Meta:
        model = LoanAccount
        fields = (
            "loan_id",
            "borrower",
            "loan_type",
            "status",
            "account_officer_id",
            "outstanding_balance",
        )
        attrs = {"class": "table table-striped"}

    def render_outstanding_balance(self, value):
        if value is not None:
            return f"₱{value:,.2f}"
        return "₱0.00"

    def __init__(self, data, user=None, **kwargs):
        super().__init__(data, **kwargs)
        # Hide account_officer_id column if user is an account officer
        if user and user.is_authenticated:
            from users.models import User

            if user.role == User.Role.ACCOUNT_OFFICER:
                self.columns.hide("account_officer_id")


class CollectionActivityLogTable(tables.Table):
    actions = tables.LinkColumn(
        "update_collection_activity",
        args=[tables.A("account.loan_id"), tables.A("activity_id")],
        verbose_name=("Actions"),
        text="Update",
        orderable=False,
    )

    class Meta:
        model = CollectionActivityLog
        fields = (
            "activity_date",
            "activity_type",
            "staff_assigned",
            "remarks",
            "promise_to_pay_date",
            "next_action_date",
            "actions",
        )
        attrs = {"class": "table table-striped"}


class DashboardCollectionActivityTable(tables.Table):
    account = tables.LinkColumn("account_detail", args=[tables.A("account.loan_id")])

    class Meta:
        model = CollectionActivityLog
        fields = ("activity_date", "account", "activity_type", "staff_assigned")
        attrs = {"class": "table table-striped"}
        orderable = False


class BorrowerAccountTable(tables.Table):
    loan_id = tables.LinkColumn("account_detail", args=[tables.A("loan_id")])

    class Meta:
        model = LoanAccount
        fields = (
            "loan_id",
            "loan_type",
            "booking_date",
            "status",
            "original_principal",
            "interest_rate",
        )
        attrs = {"class": "table table-striped"}


class ExposureTable(tables.Table):
    class Meta:
        model = Exposure
        fields = (
            "as_of_date",
            "principal_outstanding",
            "accrued_interest",
            "accrued_penalty",
            "days_past_due",
        )
        attrs = {"class": "table table-striped"}
        order_by = ("-as_of_date",)


class DelinquencyStatusTable(tables.Table):
    class Meta:
        model = DelinquencyStatus
        fields = (
            "as_of_date",
            "days_past_due",
            "aging_bucket",
            "classification",
            "npl_flag",
            "npl_date",
        )
        attrs = {"class": "table table-striped"}
        order_by = ("-as_of_date",)


class RemedialStrategyTable(tables.Table):
    strategy_type = tables.LinkColumn(
        "remedial_strategy_detail",
        args=[tables.A("account.loan_id"), tables.A("strategy_id")],
    )

    class Meta:
        model = RemedialStrategy
        fields = (
            "strategy_type",
            "strategy_start_date",
            "strategy_status",
            "strategy_outcome",
        )
        attrs = {"class": "table table-striped"}
        order_by = ("-strategy_start_date",)
