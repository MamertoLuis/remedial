from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from account_master.models import (
    Borrower,
    LoanAccount,
    CollectionActivityLog,
    RemedialStrategy,
    Exposure,
    DelinquencyStatus,
)
import account_master.services as services
from .serializers import (
    BorrowerSerializer,
    LoanAccountListSerializer,
    LoanAccountDetailSerializer,
    CollectionActivityLogSerializer,
    RemedialStrategySerializer,
    ExposureDetailSerializer,
    DelinquencyStatusSerializer,
)


class BorrowerViewSet(viewsets.ModelViewSet):
    queryset = Borrower.objects.all()
    serializer_class = BorrowerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["borrower_type", "risk_rating"]
    search_fields = ["borrower_id", "full_name", "tin"]
    ordering_fields = ["borrower_id", "full_name"]

    def perform_create(self, serializer):
        borrower_data = serializer.validated_data
        services.upsert_borrower(
            borrower_id=borrower_data["borrower_id"], defaults=borrower_data
        )

    def perform_update(self, serializer):
        borrower_data = serializer.validated_data
        borrower_id = self.get_object().borrower_id
        services.upsert_borrower(borrower_id=borrower_id, defaults=borrower_data)


class LoanAccountViewSet(viewsets.ModelViewSet):
    queryset = LoanAccount.objects.select_related("borrower").prefetch_related(
        "exposures", "delinquency_statuses", "remedial_strategies"
    )
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "loan_type", "branch_code"]
    search_fields = ["loan_id", "pn_number", "borrower__full_name"]
    ordering_fields = ["loan_id", "booking_date", "status"]

    def get_serializer_class(self):
        if self.action == "list":
            return LoanAccountListSerializer
        return LoanAccountDetailSerializer

    def perform_create(self, serializer):
        loan_data = serializer.validated_data
        services.upsert_loan_account(loan_id=loan_data["loan_id"], defaults=loan_data)

    @action(detail=True, methods=["get"], url_path="exposures")
    def exposures(self, request, pk=None):
        """Get all exposures for a specific loan account"""
        loan = self.get_object()
        exposures = loan.exposures.all()
        serializer = ExposureDetailSerializer(exposures, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="activities")
    def activities(self, request, pk=None):
        """Get all collection activities for a specific loan account"""
        loan = self.get_object()
        activities = loan.collection_activities.all()
        serializer = CollectionActivityLogSerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="strategies")
    def strategies(self, request, pk=None):
        """Get all remedial strategies for a specific loan account"""
        loan = self.get_object()
        strategies = loan.remedial_strategies.all()
        serializer = RemedialStrategySerializer(strategies, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="delinquencies")
    def delinquencies(self, request, pk=None):
        """Get all delinquency statuses for a specific loan account"""
        loan = self.get_object()
        delinquencies = loan.delinquency_statuses.all()
        serializer = DelinquencyStatusSerializer(delinquencies, many=True)
        return Response(serializer.data)


class CollectionActivityLogViewSet(viewsets.ModelViewSet):
    queryset = CollectionActivityLog.objects.select_related("account")
    serializer_class = CollectionActivityLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["activity_type", "staff_assigned"]
    search_fields = ["remarks", "staff_assigned"]
    ordering_fields = ["activity_date"]

    def perform_create(self, serializer):
        activity_data = serializer.validated_data
        account = activity_data["account"]
        services.create_collection_activity(
            account=account,
            activity_date=activity_data["activity_date"],
            activity_type=activity_data["activity_type"],
            remarks=activity_data["remarks"],
            promise_to_pay_amount=activity_data.get("promise_to_pay_amount"),
            promise_to_pay_date=activity_data.get("promise_to_pay_date"),
            staff_assigned=activity_data.get("staff_assigned"),
            next_action_date=activity_data.get("next_action_date"),
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class RemedialStrategyViewSet(viewsets.ModelViewSet):
    queryset = RemedialStrategy.objects.select_related("account")
    serializer_class = RemedialStrategySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["strategy_type", "strategy_status"]
    ordering_fields = ["strategy_start_date"]

    def perform_create(self, serializer):
        strategy_data = serializer.validated_data
        account = strategy_data["account"]
        services.create_remedial_strategy(
            account=account,
            strategy_type=strategy_data["strategy_type"],
            strategy_start_date=strategy_data["strategy_start_date"],
            strategy_status=strategy_data.get("strategy_status", "ACTIVE"),
            strategy_outcome=strategy_data.get("strategy_outcome"),
            created_by=self.request.user,
            updated_by=self.request.user,
        )
