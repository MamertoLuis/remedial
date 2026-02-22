from django.contrib import admin
from .models import CompromiseAgreement, CompromiseInstallment


@admin.register(CompromiseAgreement)
class CompromiseAgreementAdmin(admin.ModelAdmin):
    list_display = (
        "compromise_id",
        "account",
        "approved_compromise_amount",
        "approval_level",
        "status",
        "approval_date",
    )
    search_fields = ("account__loan_id", "account__borrower__full_name")
    list_filter = ("status", "approval_level", "installment_flag")
    date_hierarchy = "approval_date"


@admin.register(CompromiseInstallment)
class CompromiseInstallmentAdmin(admin.ModelAdmin):
    list_display = (
        "compromise_agreement",
        "installment_number",
        "due_date",
        "amount_due",
        "amount_paid",
        "status",
    )
    search_fields = ("compromise_agreement__account__loan_id",)
    list_filter = ("status", "due_date")
    date_hierarchy = "due_date"
