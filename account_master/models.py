from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal


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

    #: Import provenance: rows written by the iAccs import are tagged
    #: ``IACCS``; every other writer (CSV commands, app paths, dev loaders)
    #: tags ``CSV``. CSV imports must not modify ``IACCS``-tagged records.
    SOURCE_CHOICES = [
        ("IACCS", "iAccs import"),
        ("CSV", "CSV or app write"),
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
        return str(self.full_name)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("borrower_detail", args=[str(self.borrower_id)])


class RemedialStrategy(AuditableModel):
    # Stored values are stable identifiers; the display labels are the
    # recommended six names (display-only refinement, non-breaking, 5.5).
    STRATEGY_TYPE_CHOICES = [
        ("Intensive Collection", _("Intensive Collection")),
        ("Restructuring", _("Loan Restructuring / Rehabilitation")),
        ("Compromise", _("Compromise Settlement")),
        ("Foreclosure", _("Collateral Recovery / Foreclosure")),
        ("Legal Action", _("Legal Action")),
        ("Write-Off", _("Write-Off / Post-Write-off Recovery")),
    ]

    class StrategyStatus(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    strategy_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        "LoanAccount", on_delete=models.CASCADE, related_name="remedial_strategies"
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
            # (excluding any linked to this strategy), keeping at most one
            # active repayment arrangement.
            self.account.compromise_agreements.filter(
                status="ACTIVE"
            ).exclude(
                strategy_id=self.pk
            ).update(status="SUPERSEDED")

    def __str__(self):
        return str(f"{self.strategy_type} for {self.account.loan_id}")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["account", "strategy_type"],
                condition=models.Q(strategy_status="ACTIVE"),
                name="unique_active_strategy_per_account",
            )
        ]


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

    TRANSACTION_TYPE_CHOICES = [
        ("NEW", "New"),
        ("RESTRUCTURED", "Restructured"),
        ("RENEWED", "Renewed"),
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
    transaction_type = models.CharField(
        max_length=15, choices=TRANSACTION_TYPE_CHOICES, blank=True, null=True
    )

    def __str__(self):
        return str(self.loan_id)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("account_detail", args=[str(self.loan_id)])

    @property
    def has_active_remedial_strategy(self):
        """
        Returns True if the LoanAccount has at least one active RemedialStrategy,
        False otherwise.
        """
        return self.remedial_strategies.filter(
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE
        ).exists()

    @property
    def has_legal_action_strategy(self):
        """
        Returns True if the LoanAccount has an active 'Legal Action' RemedialStrategy,
        False otherwise.
        """
        return self.remedial_strategies.filter(
            strategy_type="Legal Action",
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        ).exists()

    @property
    def has_foreclosure_strategy(self):
        """
        Returns True if the LoanAccount has an active 'Foreclosure' RemedialStrategy,
        False otherwise.
        """
        return self.remedial_strategies.filter(
            strategy_type="Foreclosure",
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        ).exists()


# ============================================================================
# REMEDIAL STRATEGY FRAMEWORK MODELS
# ============================================================================


class Guarantor(AuditableModel):
    """
    Guarantor entity attached to a loan account.

    Account-level entity (persists across recommendations); an assessment
    references the guarantors relied upon at decision time.
    """

    class GuaranteeType(models.TextChoices):
        SOLIDARY = "SOLIDARY", _("Solidary")
        JOINT = "JOINT", _("Joint")
        CORPORATE = "CORPORATE", _("Corporate")

    guarantor_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="guarantors"
    )
    full_name = models.CharField(max_length=200)
    identity = models.CharField(
        max_length=100, blank=True, help_text=_("Identity document number or other identifier")
    )
    guarantee_amount = models.DecimalField(max_digits=18, decimal_places=2)
    guarantee_type = models.CharField(
        max_length=20,
        choices=GuaranteeType.choices,
        default=GuaranteeType.SOLIDARY,
    )
    is_enforceable = models.BooleanField(
        default=True, help_text=_("Whether the guarantee is legally enforceable")
    )

    class Meta:
        ordering = ["full_name"]
        verbose_name = _("Guarantor")

    def __str__(self):
        return str(f"{self.full_name} ({self.account.loan_id})")


class Collateral(AuditableModel):
    """
    Collateral entity attached to a loan account.

    Account-level entity (persists across recommendations); an assessment
    references the collaterals relied upon at decision time.
    """

    COLLATERAL_TYPE_CHOICES = [
        ("REAL_ESTATE", _("Real Estate")),
        ("VEHICLE", _("Vehicle")),
        ("EQUIPMENT", _("Equipment")),
        ("INVENTORY", _("Inventory")),
        ("DEPOSIT", _("Cash/Deposit")),
        ("OTHER", _("Other")),
    ]

    collateral_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="collaterals"
    )
    description = models.TextField()
    collateral_type = models.CharField(
        max_length=30, choices=COLLATERAL_TYPE_CHOICES, default="OTHER"
    )
    appraised_value = models.DecimalField(max_digits=18, decimal_places=2)
    as_of_date = models.DateField()

    class Meta:
        ordering = ["-as_of_date"]
        verbose_name = _("Collateral")

    def __str__(self):
        return str(f"{self.get_collateral_type_display()} for {self.account.loan_id}")


class StrategyAssessment(AuditableModel):
    """
    Assessment snapshot justifying a strategy recommendation.

    Freezes the seven decision inputs as of the recommendation date:
    delinquency, outstanding exposure, borrower financial condition,
    willingness to pay, guarantor information, collection history summary
    and recovery assessment, together with the officer's rationale.
    Re-captured on every escalation; prior snapshots stay unchanged.
    """

    FINANCIAL_CONDITION_CHOICES = [
        ("STRONG", _("Strong")),
        ("ADEQUATE", _("Adequate")),
        ("WEAK", _("Weak")),
        ("CRITICAL", _("Critical")),
    ]

    WILLINGNESS_TO_PAY_CHOICES = [
        ("HIGH", _("High")),
        ("MEDIUM", _("Medium")),
        ("LOW", _("Low")),
    ]

    RECOVERY_OUTLOOK_CHOICES = [
        ("HIGH", _("High")),
        ("MEDIUM", _("Medium")),
        ("LOW", _("Low")),
        ("NONE", _("None")),
    ]

    assessment_id = models.AutoField(primary_key=True)
    strategy = models.OneToOneField(
        RemedialStrategy, on_delete=models.CASCADE, related_name="assessment"
    )
    as_of_date = models.DateField()
    officer_rationale = models.TextField()

    # Structured judgments (ordered scales + supporting notes)
    financial_condition = models.CharField(
        max_length=20, choices=FINANCIAL_CONDITION_CHOICES, default="ADEQUATE"
    )
    financial_condition_note = models.TextField(blank=True)
    willingness_to_pay = models.CharField(
        max_length=10, choices=WILLINGNESS_TO_PAY_CHOICES, default="MEDIUM"
    )
    willingness_note = models.TextField(blank=True)
    recovery_outlook = models.CharField(
        max_length=10, choices=RECOVERY_OUTLOOK_CHOICES, default="MEDIUM"
    )
    recovery_assessment_note = models.TextField(
        blank=True, help_text=_("Basis for the recovery assessment")
    )
    expected_recovery = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    # Copied snapshot values (historical justification survives later edits)
    days_past_due = models.IntegerField(default=0)
    aging_bucket = models.CharField(max_length=10, blank=True)
    classification = models.CharField(max_length=20, blank=True)
    outstanding_exposure = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    collection_history_summary = models.TextField(blank=True)

    # Entity references relied upon at decision time
    guarantors = models.ManyToManyField(
        Guarantor, blank=True, related_name="assessments"
    )
    collaterals = models.ManyToManyField(
        Collateral, blank=True, related_name="assessments"
    )

    class Meta:
        ordering = ["-as_of_date"]
        verbose_name = _("Strategy Assessment")

    def __str__(self):
        return str(f"Assessment for {self.strategy} as of {self.as_of_date}")


class StrategyActionCatalogEntry(AuditableModel):
    """
    Reusable action template per strategy type (ladder template/instance
    pattern, mirroring ``EscalationStage``).
    """

    catalog_entry_id = models.AutoField(primary_key=True)
    strategy_type = models.CharField(
        max_length=50, choices=RemedialStrategy.STRATEGY_TYPE_CHOICES
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    ordering = models.PositiveIntegerField(default=0)
    requires_approval = models.BooleanField(default=False)

    class Meta:
        ordering = ["strategy_type", "ordering", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["strategy_type", "code"], name="uniq_catalog_entry_per_type_code"
            )
        ]
        verbose_name = _("Strategy Action Catalog Entry")

    def __str__(self):
        return str(f"{self.get_strategy_type_display()} - {self.name}")


class StrategyAction(AuditableModel):
    """
    Per-strategy instance of a catalog action with a tracked lifecycle.

    Status machine (design D3):
      SELECTED -> PENDING_APPROVAL (gated only) -> APPROVED | REJECTED
      SELECTED/APPROVED -> EXECUTED | SKIPPED
    """

    class ActionStatus(models.TextChoices):
        SELECTED = "SELECTED", _("Selected")
        PENDING_APPROVAL = "PENDING_APPROVAL", _("Pending Approval")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        EXECUTED = "EXECUTED", _("Executed")
        SKIPPED = "SKIPPED", _("Skipped")

    action_id = models.AutoField(primary_key=True)
    catalog_entry = models.ForeignKey(
        StrategyActionCatalogEntry,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    strategy = models.ForeignKey(
        RemedialStrategy, on_delete=models.CASCADE, related_name="actions"
    )
    status = models.CharField(
        max_length=20, choices=ActionStatus.choices, default=ActionStatus.SELECTED
    )
    assignee = models.CharField(
        max_length=100, blank=True, help_text=_("Staff assigned to the action")
    )
    due_date = models.DateField(null=True, blank=True)
    outcome = models.TextField(blank=True)
    executed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-action_id"]
        verbose_name = _("Strategy Action")

    def __str__(self):
        return str(f"{self.catalog_entry.code} on {self.strategy}")

    @property
    def requires_approval(self):
        return self.catalog_entry.requires_approval

    @property
    def action_code(self):
        return self.catalog_entry.code

    @property
    def is_released_for_execution(self):
        """True when the action may be executed under its class rules."""
        if self.requires_approval:
            return self.status == self.ActionStatus.APPROVED
        return self.status in [self.ActionStatus.SELECTED, self.ActionStatus.APPROVED]

    @property
    def is_in_flight(self):
        """True while the action's planning fields are editable (not terminal)."""
        return self.status in [
            self.ActionStatus.SELECTED,
            self.ActionStatus.PENDING_APPROVAL,
            self.ActionStatus.APPROVED,
        ]

    @property
    def is_skippable(self):
        """True when the officer may skip the action with a reason."""
        return self.status in [
            self.ActionStatus.SELECTED,
            self.ActionStatus.APPROVED,
        ]

    def request_approval(self):
        """Hold a gated action in the pending-approval state (D3)."""
        if not self.requires_approval:
            raise ValidationError(
                "Only approval-gated actions require manager approval."
            )
        if self.status != self.ActionStatus.SELECTED:
            raise ValidationError(
                f"Cannot request approval from status {self.status}."
            )
        self.status = self.ActionStatus.PENDING_APPROVAL
        self.save(update_fields=["status", "updated_at"])

    def mark_approved(self):
        if self.status != self.ActionStatus.PENDING_APPROVAL:
            raise ValidationError(
                f"Cannot approve an action in status {self.status}."
            )
        self.status = self.ActionStatus.APPROVED
        self.save(update_fields=["status", "updated_at"])

    def mark_rejected(self):
        if self.status != self.ActionStatus.PENDING_APPROVAL:
            raise ValidationError(
                f"Cannot reject an action in status {self.status}."
            )
        self.status = self.ActionStatus.REJECTED
        self.save(update_fields=["status", "updated_at"])

    def execute(self, *, outcome, assignee=None, executed_on=None):
        """Execute the action, recording outcome, assignee and date."""
        if self.requires_approval and self.status != self.ActionStatus.APPROVED:
            raise ValidationError(
                "Approval-gated action cannot be executed before it is approved."
            )
        if self.status not in [
            self.ActionStatus.SELECTED,
            self.ActionStatus.APPROVED,
        ]:
            raise ValidationError(
                f"Action in status {self.status} cannot be executed."
            )
        self.status = self.ActionStatus.EXECUTED
        self.outcome = outcome
        if assignee:
            self.assignee = assignee
        self.executed_on = executed_on or timezone.now().date()
        self.save(
            update_fields=["status", "outcome", "assignee", "executed_on", "updated_at"]
        )

    def skip(self, *, outcome=""):
        if self.status not in [
            self.ActionStatus.SELECTED,
            self.ActionStatus.APPROVED,
        ]:
            raise ValidationError(
                f"Action in status {self.status} cannot be skipped."
            )
        self.status = self.ActionStatus.SKIPPED
        if outcome:
            self.outcome = outcome
        self.save(update_fields=["status", "outcome", "updated_at"])


class StrategyApproval(AuditableModel):
    """
    Approval record for a gated action, carrying approver, decision, date,
    comments and any conditions attached to the approval (D4).
    """

    class Decision(models.TextChoices):
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    approval_id = models.AutoField(primary_key=True)
    action = models.ForeignKey(
        StrategyAction, on_delete=models.CASCADE, related_name="approvals"
    )
    approver = models.ForeignKey(
        get_user_model(),
        on_delete=models.PROTECT,
        related_name="strategy_approvals",
    )
    decision = models.CharField(max_length=10, choices=Decision.choices)
    decided_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    conditions = models.TextField(
        blank=True, help_text=_("Conditions attached to the approval (e.g. downpayment requirements)")
    )

    class Meta:
        ordering = ["-decided_at"]
        verbose_name = _("Strategy Approval")

    def __str__(self):
        return str(
            f"{self.get_decision_display()} on action {self.action_id} by {self.approver}"
        )


class LitigationEntry(AuditableModel):
    """
    Account-level, officer-raised, manager-approved entry to legal action.

    Records that an account is entering (or has entered) litigation so a
    Legal Action / Foreclosure strategy can be recommended without a
    terminal-stage escalation ladder. The entry is set only by an account
    officer and approved only by a manager; it is never derived from
    delinquency. At most one active (PENDING_APPROVAL or APPROVED) entry
    exists per account; a REJECTED entry does not count and may be re-raised.
    """

    class Status(models.TextChoices):
        PENDING_APPROVAL = "PENDING_APPROVAL", _("Pending Approval")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    litigation_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="litigation_entries"
    )
    strategy_type = models.CharField(
        max_length=50, choices=RemedialStrategy.STRATEGY_TYPE_CHOICES
    )
    start_date = models.DateField(help_text=_("Date litigation started / is expected"))
    rationale = models.TextField(
        default="", help_text=_("Officer rationale for entering litigation")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL
    )
    raised_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="raised_litigation_entries",
    )
    raised_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_litigation_entries",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-raised_at"]
        verbose_name = _("Litigation Entry")
        verbose_name_plural = _("Litigation Entries")
        constraints = [
            models.UniqueConstraint(
                fields=["account"],
                condition=models.Q(status__in=["PENDING_APPROVAL", "APPROVED"]),
                name="uniq_active_litigation_entry_per_account",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["account", "status"]),
        ]

    def __str__(self):
        return str(
            f"{self.get_status_display()} {self.strategy_type} for "
            f"{self.account.loan_id}"
        )


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
    action = models.ForeignKey(
        StrategyAction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidence_activities",
        help_text=_("The strategy action this activity fulfills (evidence link)"),
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
        return str(
            f"{self.activity_type} on {self.activity_date} for {self.account.loan_id}"
        )


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
    source = models.CharField(
        max_length=5, choices=Borrower.SOURCE_CHOICES, default="CSV"
    )

    principal_outstanding = models.DecimalField(max_digits=18, decimal_places=2)
    accrued_interest = models.DecimalField(max_digits=18, decimal_places=2)
    accrued_penalty = models.DecimalField(max_digits=18, decimal_places=2)
    days_past_due = models.IntegerField(default=0)
    shouldbepay = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    actualpay = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    @property
    def total_exposure(self):
        return (
            Decimal(str(self.principal_outstanding or 0))
            + Decimal(str(self.accrued_interest or 0))
            + Decimal(str(self.accrued_penalty or 0))
        )

    @property
    def collection_efficiency(self):
        """Calculate collection efficiency as (actualpay / shouldbepay) * 100"""
        if self.shouldbepay and self.shouldbepay > 0:
            return (
                Decimal(str(self.actualpay or 0)) / Decimal(str(self.shouldbepay))
            ) * 100
        return Decimal("0")

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
    source = models.CharField(
        max_length=5, choices=Borrower.SOURCE_CHOICES, default="CSV"
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

    # "Effective" flag to mark the provision used for reporting for that exposure
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
        return str(
            f"ECL {self.provision_amount} for {self.exposure.account.loan_id} as of {self.as_of_date}"
        )


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
        return str(f"{self.get_alert_type_display()}: {self.title}")

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
        NOTICE_OVERDUE = "NEXT_NOTICE_OVERDUE", _("Next Notice Overdue")

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
        through="AlertRuleRecipient",
        through_fields=("alert_rule", "user"),
        blank=True,
        related_name="alert_rules",
        help_text=_("Users to notify when rule triggers"),
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
        return str(f"{self.name} ({self.get_rule_type_display()})")

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

        # Assign to recipients - using the through model to assign
        if self.recipients.exists():
            for user in self.recipients.all():
                AlertRuleRecipient.objects.create(alert_rule=self, user=user)

        # Update rule stats
        self.last_triggered = timezone.now()
        self.trigger_count += 1
        self.save()

        return alert


class AlertRuleRecipient(models.Model):
    """
    Intermediate model for AlertRule and User ManyToMany relationship.
    """

    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("alert_rule", "user")

    def __str__(self):
        return str(f"{self.alert_rule.name} - {self.user.username}")


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
        return str(f"{self.alert.title} - {self.action_taken}")


# ============================================================================
# NOTICE ESCALATION LADDER MODELS (judgment plane)
# ============================================================================


class EscalationStage(AuditableModel):
    """
    Fixed ladder template of ordered escalation stages (judgment plane).

    Durations are tunable in Django admin; stage order is by ``stage_no``.
    """

    stage_no = models.PositiveIntegerField(
        unique=True, help_text=_("Ladder position (1 = first stage)")
    )
    label = models.CharField(max_length=100, help_text=_("Stage label e.g. First Demand"))
    duration_days = models.PositiveIntegerField(
        help_text=_("Days until the next notice is due")
    )
    is_terminal = models.BooleanField(
        default=False,
        help_text=_("Last escalation stage; issuing a notice here closes the ladder"),
    )

    class Meta:
        ordering = ["stage_no"]
        verbose_name = _("Escalation Stage")
        verbose_name_plural = _("Escalation Stages")

    def __str__(self):
        return str(f"{self.stage_no}. {self.label}")


class EscalationState(AuditableModel):
    """
    One escalation position per loan account.

    Carries the current stage, the date the stage started, the computed
    next-notice due date, and a lifecycle status. An account holds at most
    one open (PENDING/ACTIVE/PAUSED) state at a time.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        ACTIVE = "ACTIVE", _("Active")
        PAUSED = "PAUSED", _("Paused")
        CLOSED = "CLOSED", _("Closed")

    class CloseReason(models.TextChoices):
        CURED = "cured", _("Cured")
        ARRANGEMENT = "arrangement", _("Arrangement approved")
        TERMINAL = "terminal", _("Terminal stage")

    escalation_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="escalation_states"
    )
    current_stage = models.ForeignKey(
        EscalationStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escalation_states",
    )
    stage_started_on = models.DateField()
    next_notice_due = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    closed_reason = models.CharField(
        max_length=20, choices=CloseReason.choices, null=True, blank=True
    )

    class Meta:
        ordering = ["-stage_started_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["account"],
                condition=models.Q(status__in=["PENDING", "ACTIVE", "PAUSED"]),
                name="uniq_open_escalation_state_per_account",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["account", "status"]),
            models.Index(fields=["next_notice_due"]),
        ]

    @property
    def is_open(self):
        return self.status in [
            self.Status.PENDING,
            self.Status.ACTIVE,
            self.Status.PAUSED,
        ]

    def __str__(self):
        return str(f"Escalation ({self.get_status_display()}) - {self.account.loan_id}")


class Notice(AuditableModel):
    """
    History of notices issued against an account's escalation ladder.
    """

    class Method(models.TextChoices):
        LETTER = "Letter", _("Letter")
        EMAIL = "Email", _("Email")
        SMS = "SMS", _("SMS")
        PHONE = "Phone", _("Phone Call")

    notice_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(
        LoanAccount, on_delete=models.CASCADE, related_name="notices"
    )
    stage = models.ForeignKey(
        EscalationStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notices",
    )
    issued_on = models.DateField()
    method = models.CharField(max_length=20, choices=Method.choices)
    issued_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_notices",
    )
    reference_no = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["-issued_on"]
        indexes = [
            models.Index(fields=["account", "issued_on"]),
        ]

    def __str__(self):
        return str(
            f"{self.get_method_display()} notice issued {self.issued_on} for {self.account.loan_id}"
        )


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
