from django.contrib import admin
from .models import (
    LoanAccount,
    Borrower,
    CollectionActivityLog,
    RemedialStrategy,
    Exposure,
    DelinquencyStatus,
    ECLProvisionHistory,
    Alert,
    AlertRule,
    AlertLog,
)
from . import services
from .services.provision_service import create_provision_entry


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = (
        "borrower_id",
        "full_name",
        "borrower_type",
        "mobile",
        "borrower_group",
    )
    search_fields = ("borrower_id", "full_name", "mobile", "borrower_group")
    list_filter = ("borrower_type", "borrower_group")


@admin.register(LoanAccount)
class LoanAccountAdmin(admin.ModelAdmin):
    list_display = (
        "loan_id",
        "borrower",
        "loan_type",
        "status",
        "account_officer_id",
        "booking_date",
    )
    search_fields = (
        "loan_id",
        "borrower__full_name",
        "borrower__borrower_id",
        "account_officer_id",
    )
    list_filter = ("status", "loan_type", "loan_security")


@admin.register(Exposure)
class ExposureAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "as_of_date",
        "principal_outstanding",
        "days_past_due",
        "snapshot_type",
    )
    search_fields = ("account__loan_id", "account__borrower__full_name")
    list_filter = ("snapshot_type", "as_of_date")
    date_hierarchy = "as_of_date"

    def save_model(self, request, obj, form, change):
        exposure_data = {
            "principal_outstanding": obj.principal_outstanding,
            "accrued_interest": obj.accrued_interest,
            "accrued_penalty": obj.accrued_penalty,
            "days_past_due": obj.days_past_due,
            "snapshot_type": obj.snapshot_type,
        }
        services.upsert_exposure(
            account=obj.account, as_of_date=obj.as_of_date, defaults=exposure_data
        )


@admin.register(DelinquencyStatus)
class DelinquencyStatusAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "as_of_date",
        "days_past_due",
        "aging_bucket",
        "classification",
        "npl_flag",
    )
    search_fields = ("account__loan_id", "account__borrower__full_name")
    list_filter = ("classification", "npl_flag", "aging_bucket", "snapshot_type")
    date_hierarchy = "as_of_date"

    def save_model(self, request, obj, form, change):
        delinquency_data = {
            "days_past_due": obj.days_past_due,
            "aging_bucket": obj.aging_bucket,
            "classification": obj.classification,
            "npl_flag": obj.npl_flag,
            "npl_date": obj.npl_date,
            "snapshot_type": obj.snapshot_type,
        }
        services.upsert_delinquency_status(
            account=obj.account, as_of_date=obj.as_of_date, defaults=delinquency_data
        )


@admin.register(ECLProvisionHistory)
class ECLProvisionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "exposure",
        "as_of_date",
        "provision_rate",
        "provision_amount",
        "method",
        "is_current",
    )
    search_fields = ("exposure__account__loan_id",)
    list_filter = ("method", "is_current", "classification")
    date_hierarchy = "as_of_date"

    def save_model(self, request, obj, form, change):
        create_provision_entry(
            exposure=obj.exposure,
            provision_rate=obj.provision_rate,
            method=obj.method,
            remarks=obj.remarks,
            classification=obj.classification,
            days_past_due=obj.days_past_due,
            user=request.user,
        )


@admin.register(CollectionActivityLog)
class CollectionActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "activity_date",
        "activity_type",
        "staff_assigned",
        "promise_to_pay_date",
    )
    search_fields = ("account__loan_id", "staff_assigned", "remarks")
    list_filter = ("activity_type", "activity_date")
    date_hierarchy = "activity_date"


@admin.register(RemedialStrategy)
class RemedialStrategyAdmin(admin.ModelAdmin):
    list_display = (
        "account",
        "strategy_type",
        "strategy_start_date",
        "strategy_status",
    )
    search_fields = ("account__loan_id",)
    list_filter = ("strategy_type", "strategy_status")
    date_hierarchy = "strategy_start_date"


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "alert_type",
        "severity",
        "status",
        "entity_type",
        "entity_id",
        "created_at",
    )
    search_fields = ("title", "message", "entity_id")
    list_filter = ("alert_type", "severity", "status", "entity_type")
    date_hierarchy = "created_at"


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "rule_type",
        "condition_value",
        "comparison_operator",
        "is_active",
        "alert_type",
    )
    search_fields = ("name", "description")
    list_filter = ("rule_type", "is_active", "alert_type", "severity")


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = (
        "alert",
        "action_taken",
        "performed_by",
        "timestamp",
        "previous_status",
        "new_status",
    )
    search_fields = ("alert__title", "action_taken")
    list_filter = ("timestamp",)
    date_hierarchy = "timestamp"
