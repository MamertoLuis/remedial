import django_tables2 as tables
from django.utils.html import format_html
from django.urls import reverse
from .models import CompromiseAgreement, CompromiseInstallment


class CompromiseAgreementTable(tables.Table):
    collapse_columns = ["discount_amount", "discount_percentage"]
    borrower = tables.TemplateColumn(
        template_name="compromise_agreement/_borrower_column.html",
        verbose_name="Borrower",
        orderable=False,
    )

    account = tables.TemplateColumn(
        template_name="compromise_agreement/_account_column.html",
        verbose_name="Account",
    )

    actions = tables.TemplateColumn(
        template_name="compromise_agreement/_actions.html", verbose_name="Actions"
    )

    class Meta:
        model = CompromiseAgreement
        empty_text = "No records found."
        fields = (
            "compromise_id",
            "borrower",
            "account",
            "original_total_exposure",
            "approved_compromise_amount",
            "discount_amount",
            "discount_percentage",
            "status",
            "actions",
        )


class CompromiseInstallmentTable(tables.Table):
    collapse_columns = ["payment_date"]
    actions = tables.TemplateColumn(
        template_name="compromise_agreement/_installment_actions.html",
        verbose_name="Actions",
    )

    class Meta:
        model = CompromiseInstallment
        empty_text = "No records found."
        fields = (
            "installment_number",
            "due_date",
            "amount_due",
            "amount_paid",
            "payment_date",
            "status",
            "actions",
        )
