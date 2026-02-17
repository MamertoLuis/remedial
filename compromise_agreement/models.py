from django.db import models
from django.utils.translation import gettext_lazy as _
from account_master.models import LoanAccount
from django.contrib.auth import get_user_model

User = get_user_model()

class CompromiseAgreement(models.Model):
    class ApprovalLevel(models.TextChoices):
        AO = 'AO', _('Account Officer')
        MANAGER = 'MANAGER', _('Manager')
        BOARD = 'BOARD', _('Board')

    class CompromiseStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        COMPLETED = 'COMPLETED', _('Completed')
        RESCINDED = 'RESCINDED', _('Rescinded')

    compromise_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(LoanAccount, on_delete=models.CASCADE, related_name='compromise_agreements')
    original_total_exposure = models.DecimalField(max_digits=15, decimal_places=2)
    approved_compromise_amount = models.DecimalField(max_digits=15, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, editable=False)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    approval_level = models.CharField(max_length=10, choices=ApprovalLevel.choices)
    approval_date = models.DateField()
    installment_flag = models.BooleanField(default=False)
    rescission_clause_flag = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=CompromiseStatus.choices, default=CompromiseStatus.ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='compromise_agreements_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='compromise_agreements_updated')

    def save(self, *args, **kwargs):
        self.discount_amount = self.original_total_exposure - self.approved_compromise_amount
        if self.original_total_exposure > 0:
            self.discount_percentage = (self.discount_amount / self.original_total_exposure) * 100
        else:
            self.discount_percentage = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Compromise for {self.account.loan_id}"

class CompromiseInstallment(models.Model):
    class InstallmentStatus(models.TextChoices):
        PAID = 'PAID', _('Paid')
        UNPAID = 'UNPAID', _('Unpaid')

    installment_id = models.AutoField(primary_key=True)
    compromise_agreement = models.ForeignKey(CompromiseAgreement, on_delete=models.CASCADE, related_name='installments')
    installment_number = models.IntegerField()
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=InstallmentStatus.choices, default=InstallmentStatus.UNPAID)

    def __str__(self):
        return f"Installment {self.installment_number} for {self.compromise_agreement.compromise_id}"
