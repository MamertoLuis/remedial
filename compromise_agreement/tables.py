import django_tables2 as tables
from .models import CompromiseAgreement, CompromiseInstallment

class CompromiseAgreementTable(tables.Table):
    actions = tables.TemplateColumn(
        template_name='compromise_agreement/_actions.html',
        verbose_name='Actions'
    )

    class Meta:
        model = CompromiseAgreement
        template_name = "django_tables2/bootstrap5.html"
        fields = (
            'compromise_id',
            'account',
            'original_total_exposure',
            'approved_compromise_amount',
            'discount_amount',
            'discount_percentage',
            'status',
            'actions'
        )

class CompromiseInstallmentTable(tables.Table):
    actions = tables.TemplateColumn(
        '<a href="{% url \'compromise_installment_update\' record.pk %}" class="btn btn-sm btn-warning">Update</a>',
        verbose_name='Actions'
    )

    class Meta:
        model = CompromiseInstallment
        template_name = "django_tables2/bootstrap5.html"
        fields = (
            'installment_number',
            'due_date',
            'amount_due',
            'amount_paid',
            'payment_date',
            'status',
            'actions'
        )
