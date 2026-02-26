from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
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
    borrower_group = models.CharField(
        max_length=100, default=None, null=True, blank=True
    )

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("borrower_detail", args=[str(self.borrower_id)])


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

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("account_detail", args=[str(self.loan_id)])


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


# ============================================================================
# ALERT SYSTEM MODELS
# ============================================================================


class Alert(AuditableModel):
    """
    Alert model for tracking notifications and important events
    in the loan remedial management system.
    """

    class AlertType(models.TextChoices):
        CRITICAL = "CRITICAL", _("Critical")
        WARNING = "WARNING", _("Warning")
        INFO = "INFO", _("Info")
        SUCCESS = "SUCCESS", _("Success")

    class Severity(models.TextChoices):
        HIGH = "HIGH", _("High")
        MEDIUM = "MEDIUM", _("Medium")
        LOW = "LOW", _("Low")

    class Status(models.TextChoices):
        NEW = "NEW", _("New")
        ACKNOWLEDGED = "ACKNOWLEDGED", _("Acknowledged")
        RESOLVED = "RESOLVED", _("Resolved")
        DISMISSED = "DISMISSED", _("Dismissed")

    class EntityType(models.TextChoices):
        ACCOUNT = "ACCOUNT", _("Loan Account")
        BORROWER = "BORROWER", _("Borrower")
        COMPROMISE_AGREEMENT = "COMPROMISE_AGREEMENT", _("Compromise Agreement")
        DELINQUENCY_STATUS = "DELINQUENCY_STATUS", _("Delinquency Status")
        REMEDIAL_STRATEGY = "REMEDIAl_STRATEGY", _("Remedial Strategy")
        EXPOSURE = "EXPOSURE", _("Exposure")
        SYSTEM = "SYSTEM", _("System")

    alert_id = models.AutoField(primary_key=True)
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        default=AlertType.INFO,
        help_text=_("Type of alert"),
    )

    title = models.CharField(max_length=200, help_text=_("Short alert headline"))

    message = models.TextField(help_text=_("Detailed alert description"))

    entity_type = models.CharField(
        max_length=30, choices=EntityType.choices, help_text=_("Type of related entity")
    )

    entity_id = models.CharField(
        max_length=50, blank=True, null=True, help_text=_("ID of related entity")
    )

    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        help_text=_("Priority level of alert"),
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.NEW,
        help_text=_("Current status of alert"),
    )

    due_date = models.DateField(
        blank=True, null=True, help_text=_("Optional deadline for action")
    )

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts_created",
        help_text=_("User who created or triggered the alert"),
    )

    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts_assigned",
        help_text=_("User responsible for addressing the alert"),
    )

    metadata = models.JSONField(
        default=dict, blank=True, help_text=_("Additional alert data stored as JSON")
    )

    is_read = models.BooleanField(
        default=False,
        help_text=_("Whether the alert has been read by the assigned user"),
    )

    expires_at = models.DateTimeField(
        blank=True, null=True, help_text=_("Optional expiration time for the alert")
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "severity"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.title}"

    def get_entity_url(self):
        """Get URL for the related entity."""
        if not self.entity_type or not self.entity_id:
            return None

        url_mapping = {
            self.EntityType.ACCOUNT: f"/account/{self.entity_id}/",
            self.EntityType.BORROWER: f"/borrower/{self.entity_id}/",
            self.EntityType.COMPROMISE_AGREEMENT: f"/compromise/{self.entity_id}/",
            self.EntityType.DELINQUENCY_STATUS: f"/account/{self.entity_id}/#delinquency",
            self.EntityType.REMEDIAL_STRATEGY: f"/account/{self.entity_id}/#strategy",
            self.EntityType.EXPOSURE: f"/account/{self.entity_id}/#exposure",
            self.EntityType.SYSTEM: "#",
        }

        return url_mapping.get(self.entity_type)

    def is_overdue(self):
        """Check if alert is overdue."""
        if not self.due_date or self.status in [
            self.Status.RESOLVED,
            self.Status.DISMISSED,
        ]:
            return False
        return self.due_date < timezone.now().date()

    def is_expired(self):
        """Check if alert has expired."""
        if not self.expires_at:
            return False
        return self.expires_at < timezone.now()

    def acknowledge(self, user=None):
        """Mark alert as acknowledged."""
        if self.status != self.Status.NEW:
            return False

        self.status = self.Status.ACKNOWLEDGED
        self.save()

        # Log the action
        AlertLog.objects.create(
            alert=self,
            action_taken=_("Alert acknowledged"),
            performed_by=user,
            previous_status=self.Status.NEW,
            new_status=self.Status.ACKNOWLEDGED,
        )
        return True

    def resolve(self, user=None, resolution_notes=""):
        """Mark alert as resolved."""
        if self.status in [self.Status.RESOLVED, self.Status.DISMISSED]:
            return False

        previous_status = self.status
        self.status = self.Status.RESOLVED
        self.save()

        # Log the action
        AlertLog.objects.create(
            alert=self,
            action_taken=_("Alert resolved")
            + (f": {resolution_notes}" if resolution_notes else ""),
            performed_by=user,
            previous_status=previous_status,
            new_status=self.Status.RESOLVED,
        )
        return True

    def dismiss(self, user=None, reason=""):
        """Dismiss alert."""
        if self.status in [self.Status.RESOLVED, self.Status.DISMISSED]:
            return False

        previous_status = self.status
        self.status = self.Status.DISMISSED
        self.save()

        # Log the action
        AlertLog.objects.create(
            alert=self,
            action_taken=_("Alert dismissed") + (f": {reason}" if reason else ""),
            performed_by=user,
            previous_status=previous_status,
            new_status=self.Status.DISMISSED,
        )
        return True

    @property
    def urgency_class(self):
        """Get Bootstrap class based on severity."""
        class_mapping = {
            self.Severity.HIGH: "danger",
            self.Severity.MEDIUM: "warning",
            self.Severity.LOW: "info",
        }
        return class_mapping.get(self.severity, "secondary")

    @property
    def type_icon(self):
        """Get Bootstrap icon based on alert type."""
        icon_mapping = {
            self.AlertType.CRITICAL: "bi-exclamation-triangle-fill",
            self.AlertType.WARNING: "bi-exclamation-circle-fill",
            self.AlertType.INFO: "bi-info-circle-fill",
            self.AlertType.SUCCESS: "bi-check-circle-fill",
        }
        return icon_mapping.get(self.alert_type, "bi-bell-fill")


class AlertRule(AuditableModel):
    """
    Alert rule model for automated alert generation.
    """

    class RuleType(models.TextChoices):
        DPD_THRESHOLD = "DPD_THRESHOLD", _("DPD Threshold")
        EXPOSURE_LIMIT = "EXPOSURE_LIMIT", _("Exposure Limit")
        STATUS_CHANGE = "STATUS_CHANGE", _("Status Change")
        AGREEMENT_DEADLINE = "AGREEMENT_DEADLINE", _("Agreement Deadline")
        COLLECTION_INACTIVITY = "COLLECTION_INACTIVITY", _("Collection Inactivity")
        NPL_RATIO = "NPL_RATIO", _("NPL Ratio")
        PROVISION_COVERAGE = "PROVISION_COVERAGE", _("Provision Coverage")

    class ComparisonOperator(models.TextChoices):
        GREATER_THAN = ">", _("Greater than")
        LESS_THAN = "<", _("Less than")
        GREATER_EQUAL = ">=", _("Greater than or equal")
        LESS_EQUAL = "<=", _("Less than or equal")
        EQUAL = "==", _("Equal")
        NOT_EQUAL = "!=", _("Not equal")

    rule_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, help_text=_("Rule identifier"))

    description = models.TextField(help_text=_("Description of the rule's purpose"))

    rule_type = models.CharField(
        max_length=30,
        choices=RuleType.choices,
        help_text=_("Type of condition to check"),
    )

    condition_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_("Threshold value for the condition"),
    )

    comparison_operator = models.CharField(
        max_length=2,
        choices=ComparisonOperator.choices,
        default=ComparisonOperator.GREATER_EQUAL,
        help_text=_("Comparison operator for the condition"),
    )

    is_active = models.BooleanField(
        default=True, help_text=_("Whether the rule is active")
    )

    alert_type = models.CharField(
        max_length=20,
        choices=Alert.AlertType.choices,
        default=Alert.AlertType.WARNING,
        help_text=_("Type of alert to generate when triggered"),
    )

    severity = models.CharField(
        max_length=10,
        choices=Alert.Severity.choices,
        default=Alert.Severity.MEDIUM,
        help_text=_("Severity level for generated alerts"),
    )

    notification_channels = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of notification channels (['in_app', 'email', 'sms'])"),
    )

    recipients = models.ManyToManyField(
        "users.User",
        blank=True,
        related_name="alert_rules",
        help_text=_("Users to notify when rule triggers"),
    )

    metadata = models.JSONField(
        default=dict, blank=True, help_text=_("Additional rule configuration")
    )

    last_triggered = models.DateTimeField(
        blank=True, null=True, help_text=_("When the rule was last triggered")
    )

    trigger_count = models.PositiveIntegerField(
        default=0, help_text=_("Number of times this rule has been triggered")
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["rule_type", "is_active"]),
            models.Index(fields=["last_triggered"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"

    def evaluate_condition(self, value):
        """Evaluate if the condition is met."""
        condition_value = float(self.condition_value)
        test_value = float(value) if value is not None else 0

        operator_mapping = {
            self.ComparisonOperator.GREATER_THAN: lambda x, y: x > y,
            self.ComparisonOperator.LESS_THAN: lambda x, y: x < y,
            self.ComparisonOperator.GREATER_EQUAL: lambda x, y: x >= y,
            self.ComparisonOperator.LESS_EQUAL: lambda x, y: x <= y,
            self.ComparisonOperator.EQUAL: lambda x, y: x == y,
            self.ComparisonOperator.NOT_EQUAL: lambda x, y: x != y,
        }

        operator_func = operator_mapping.get(self.comparison_operator)
        if not operator_func:
            return False

        return operator_func(test_value, condition_value)

    def trigger_alert(self, entity_type, entity_id, title, message, metadata=None):
        """Create an alert when rule is triggered."""
        if not self.is_active:
            return None

        alert = Alert.objects.create(
            alert_type=self.alert_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=self.severity,
            metadata=metadata or {},
        )

        # Assign to recipients
        if self.recipients.exists():
            alert.assigned_to.set(self.recipients.all())

        # Update rule stats
        self.last_triggered = timezone.now()
        self.trigger_count += 1
        self.save()

        return alert


class AlertLog(AuditableModel):
    """
    Log model for tracking alert history and actions.
    """

    log_id = models.AutoField(primary_key=True)
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name="logs",
        help_text=_("Related alert"),
    )

    action_taken = models.CharField(
        max_length=200, help_text=_("Description of action taken")
    )

    performed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_actions",
        help_text=_("User who performed the action"),
    )

    timestamp = models.DateTimeField(
        auto_now_add=True, help_text=_("When the action was performed")
    )

    previous_status = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text=_("Alert status before the action"),
    )

    new_status = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text=_("Alert status after the action"),
    )

    notes = models.TextField(
        blank=True, null=True, help_text=_("Additional notes about the action")
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["alert", "timestamp"]),
            models.Index(fields=["performed_by"]),
        ]

    def __str__(self):
        return f"{self.alert.title} - {self.action_taken}"


# Import signals at the end to avoid circular imports
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=DelinquencyStatus)
def update_ecl_provision_on_delinquency_change(sender, instance, created, **kwargs):
    """
    Automatically update ECL provision when DelinquencyStatus is created or updated.
    """
    try:
        from .services import update_ecl_provision_for_account

        # Always update ECL provisions for this account and date when delinquency changes
        update_ecl_provision_for_account(
            account=instance.account, as_of_date=instance.as_of_date
        )

    except Exception as e:
        # Log the error but don't raise it to avoid breaking the save operation
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Error updating ECL provision for delinquency {instance.delinquency_id}: {e}"
        )
