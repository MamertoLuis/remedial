from django.db import models
from django.contrib.auth import get_user_model


class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        get_user_model(),
        related_name="%(class)s_created_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        get_user_model(),
        related_name="%(class)s_updated_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class Borrower(AuditableModel):
    BORROWER_TYPE_CHOICES = [
        ("PERSON", "Person"),
        ("CORP", "Corporation"),
        ("COOP", "Cooperative"),
    ]

    borrower_id = models.CharField(max_length=20, primary_key=True)
    borrower_type = models.CharField(
        max_length=10, choices=BORROWER_TYPE_CHOICES, default="PERSON"
    )
    full_name = models.CharField(max_length=200)
    primary_address = models.CharField(max_length=300)
    mobile = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.full_name


class LoanAccount(AuditableModel):
    LOAN_STATUS_CHOICES = [
        ("PERFORMING", "Performing"),
        ("PAST_DUE", "Past Due"),
        ("NPL", "NPL"),
        ("WRITEOFF", "Write-Off"),
        ("CLOSED", "Closed"),
    ]

    LOAN_SECURITY_CHOICES = [
        ("SECURED", "Secured"),
        ("UNSECURED", "Unsecured"),
    ]

    loan_id = models.CharField(max_length=20, primary_key=True)
    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE)
    booking_date = models.DateField()
    maturity_date = models.DateField()
    original_principal = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    loan_type = models.CharField(max_length=50)
    loan_security = models.CharField(
        max_length=10, choices=LOAN_SECURITY_CHOICES, default="UNSECURED"
    )
    account_officer_id = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20, choices=LOAN_STATUS_CHOICES, default="PERFORMING"
    )

    def __str__(self):
        return self.loan_id


class CollectionActivityLog(AuditableModel):
    ACTIVITY_TYPE_CHOICES = [
        ("Call", "Call"),
        ("Visit", "Visit"),
        ("Demand Letter", "Demand Letter"),
        ("Negotiation", "Negotiation"),
    ]

    activity_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="collection_activities"
    )
    activity_date = models.DateField()
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    remarks = models.TextField()
    promise_to_pay_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    promise_to_pay_date = models.DateField(null=True, blank=True)
    staff_assigned = models.CharField(max_length=100)
    next_action_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.activity_type} on {self.activity_date} for {self.account.loan_id}"
        )


from django.utils.translation import gettext_lazy as _


class RemedialStrategy(AuditableModel):
    STRATEGY_TYPE_CHOICES = [
        ("Intensive Collection", _("Intensive Collection")),
        ("Restructuring", _("Restructuring")),
        ("Compromise", _("Compromise")),
        ("Foreclosure", _("Foreclosure")),
        ("Legal Action", _("Legal Action")),
        ("Write-Off", _("Write-Off")),
    ]

    class StrategyStatus(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    strategy_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="remedial_strategies"
    )
    strategy_type = models.CharField(max_length=50, choices=STRATEGY_TYPE_CHOICES)
    strategy_start_date = models.DateField()
    strategy_status = models.CharField(
        max_length=10, choices=StrategyStatus.choices, default=StrategyStatus.ACTIVE
    )
    strategy_outcome = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.strategy_status == self.StrategyStatus.ACTIVE:
            # Deactivate any other active strategies for the same account
            RemedialStrategy.objects.filter(
                account=self.account, strategy_status=self.StrategyStatus.ACTIVE
            ).exclude(pk=self.pk).update(strategy_status=self.StrategyStatus.CANCELLED)

            # Supersede any active compromise agreements for the same account
            self.account.compromise_agreements.filter(status="ACTIVE").exclude(
                strategy=self
            ).update(status="SUPERSEDED")

    def __str__(self):
        return f"{self.strategy_type} for {self.account.loan_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "strategy_type"],
                condition=models.Q(strategy_status="ACTIVE"),
                name="unique_active_strategy_per_account",
            )
        ]


class Exposure(AuditableModel):
    SNAPSHOT_TYPE = [
        ("EVENT", "Event-driven"),
        ("MONTH_END", "Month-end"),
    ]

    exposure_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="exposures"
    )

    as_of_date = models.DateField()
    snapshot_type = models.CharField(
        max_length=10, choices=SNAPSHOT_TYPE, default="EVENT"
    )

    principal_outstanding = models.DecimalField(max_digits=18, decimal_places=2)
    accrued_interest = models.DecimalField(max_digits=18, decimal_places=2)
    accrued_penalty = models.DecimalField(max_digits=18, decimal_places=2)
    days_past_due = models.IntegerField(default=0)

    @property
    def total_exposure(self):
        return self.principal_outstanding + self.accrued_interest + self.accrued_penalty

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "as_of_date"], name="uniq_exposure_account_asof"
            )
        ]
        indexes = [
            models.Index(fields=["as_of_date"]),
            models.Index(fields=["account", "as_of_date"]),
            models.Index(fields=["snapshot_type", "as_of_date"]),
        ]


class DelinquencyStatus(AuditableModel):
    AGING_BUCKET_CHOICES = [
        ("Current", "Current"),
        ("1-30", "1-30"),
        ("31-60", "31-60"),
        ("61-90", "61-90"),
        ("91-120", "91-120"),
        ("121-180", "121-180"),
        ("181-360", "181-360"),
        ("Over 360", "Over 360"),
    ]

    CLASSIFICATION_CHOICES = [
        ("C", "Current"),
        ("SM", "Especially Mentioned"),
        ("SS", "Substandard"),
        ("D", "Doubtful"),
        ("L", "Loss"),
    ]

    SNAPSHOT_TYPE = [
        ("EVENT", "Event-driven"),
        ("MONTH_END", "Month-end"),
    ]

    delinquency_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="delinquency_statuses"
    )

    as_of_date = models.DateField()
    snapshot_type = models.CharField(
        max_length=10, choices=SNAPSHOT_TYPE, default="EVENT"
    )

    days_past_due = models.IntegerField(default=0)

    aging_bucket = models.CharField(
        max_length=10, choices=AGING_BUCKET_CHOICES, blank=True, null=True
    )
    classification = models.CharField(
        max_length=20, choices=CLASSIFICATION_CHOICES, default="C"
    )
    npl_flag = models.BooleanField(default=False)
    npl_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "as_of_date"], name="uniq_delinquency_account_asof"
            )
        ]
        indexes = [
            models.Index(fields=["as_of_date"]),
            models.Index(fields=["account", "as_of_date"]),
            models.Index(fields=["classification", "as_of_date"]),
            models.Index(fields=["npl_flag", "as_of_date"]),
        ]


class ECLProvisionHistory(AuditableModel):
    METHOD_CHOICES = [
        ("MANUAL", "Manual"),
        ("RULE_BASED", "Rule-based"),
        ("IFRS9", "IFRS 9"),
        ("IMPORT", "Imported"),
    ]

    provision_id = models.AutoField(primary_key=True)

    # Link to snapshot, not just account
    exposure = models.ForeignKey(
        "Exposure", on_delete=models.CASCADE, related_name="provision_history"
    )

    as_of_date = (
        models.DateField()
    )  # duplicated for query speed / reporting convenience

    # Provision result
    provision_rate = models.DecimalField(
        max_digits=7, decimal_places=4
    )  # ex: 0.2500 = 25.00%
    provision_amount = models.DecimalField(max_digits=18, decimal_places=2)

    # Optional: classification basis used at the time (for audit trail)
    classification = models.CharField(
        max_length=20, blank=True, null=True
    )  # e.g. C/SM/SS/D/L
    days_past_due = models.IntegerField(null=True, blank=True)

    # Metadata
    method = models.CharField(
        max_length=20, choices=METHOD_CHOICES, default="RULE_BASED"
    )
    remarks = models.TextField(blank=True, default="")

    # “Effective” flag to mark the provision used for reporting for that exposure
    is_current = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["as_of_date"]),
            models.Index(fields=["exposure", "is_current"]),
            models.Index(fields=["is_current", "as_of_date"]),
        ]
        constraints = [
            # Only one "current" provisioning per exposure
            models.UniqueConstraint(
                fields=["exposure"],
                condition=models.Q(is_current=True),
                name="uniq_current_provision_per_exposure",
            )
        ]

    def __str__(self):
        return f"ECL {self.provision_amount} for {self.exposure.account.loan_id} as of {self.as_of_date}"
