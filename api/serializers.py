from rest_framework import serializers
from account_master.models import (
    Borrower,
    LoanAccount,
    CollectionActivityLog,
    RemedialStrategy,
    Exposure,
    DelinquencyStatus,
)


class BorrowerSerializer(serializers.ModelSerializer):
    loans_count = serializers.SerializerMethodField()

    class Meta:
        model = Borrower
        fields = [
            "borrower_id",
            "borrower_type",
            "full_name",
            "tin",
            "primary_address",
            "mobile",
            "email",
            "risk_rating",
            "loans_count",
        ]

    def get_loans_count(self, obj):
        # Check if obj is a model instance or just data
        if hasattr(obj, "loanaccount_set"):
            return obj.loanaccount_set.count()
        # If it's just data (OrderedDict), return 0
        return 0


class LoanAccountListSerializer(serializers.ModelSerializer):
    borrower = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = LoanAccount
        fields = [
            "loan_id",
            "borrower",
            "loan_type",
            "status",
            "booking_date",
            "original_principal",
        ]


class LoanAccountDetailSerializer(serializers.ModelSerializer):
    borrower = BorrowerSerializer(read_only=True)
    current_exposure = serializers.SerializerMethodField()
    current_delinquency = serializers.SerializerMethodField()
    active_strategy = serializers.SerializerMethodField()

    class Meta:
        model = LoanAccount
        fields = "__all__"

    def get_current_exposure(self, obj):
        exposure = obj.exposures.order_by("-as_of_date").first()
        return ExposureDetailSerializer(exposure).data if exposure else None

    def get_current_delinquency(self, obj):
        delinquency = obj.delinquency_statuses.order_by("-as_of_date").first()
        return DelinquencyStatusSerializer(delinquency).data if delinquency else None

    def get_active_strategy(self, obj):
        strategy = obj.remedial_strategies.filter(strategy_status="ACTIVE").first()
        return RemedialStrategySerializer(strategy).data if strategy else None


class ExposureDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exposure
        fields = [
            "exposure_id",
            "as_of_date",
            "principal_outstanding",
            "accrued_interest",
            "accrued_penalty",
            "total_exposure",
            "provision_amount",
            "provision_rate",
        ]


class DelinquencyStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DelinquencyStatus
        fields = [
            "delinquency_id",
            "as_of_date",
            "days_past_due",
            "aging_bucket",
            "classification",
            "npl_flag",
        ]


class CollectionActivityLogSerializer(serializers.ModelSerializer):
    account = LoanAccountListSerializer(read_only=True)

    class Meta:
        model = CollectionActivityLog
        fields = [
            "activity_id",
            "account",
            "activity_date",
            "activity_type",
            "remarks",
            "promise_to_pay_amount",
            "promise_to_pay_date",
            "staff_assigned",
            "next_action_date",
        ]


class RemedialStrategySerializer(serializers.ModelSerializer):
    account = LoanAccountListSerializer(read_only=True)

    class Meta:
        model = RemedialStrategy
        fields = [
            "strategy_id",
            "account",
            "strategy_type",
            "strategy_start_date",
            "strategy_status",
            "strategy_outcome",
        ]
