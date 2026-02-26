from django.db.models import Q, F
from django.utils import timezone
from datetime import timedelta, datetime
import logging

from ..models import (
    LoanAccount,
    Borrower,
    DelinquencyStatus,
    RemedialStrategy,
    CollectionActivityLog,
)
from compromise_agreement.models import CompromiseAgreement

logger = logging.getLogger(__name__)


class ActivityService:
    """
    Service class for tracking and aggregating activities across the system.
    Provides unified interface for different types of activities.
    """

    ACTIVITY_TYPES = {
        "collection": "Collection Activity",
        "compromise": "Compromise Agreement",
        "strategy": "Remedial Strategy",
        "delinquency": "Delinquency Status",
        "exposure": "Exposure Snapshot",
    }

    @classmethod
    def get_recent_activities(cls, limit=20, activity_types=None, date_range=None):
        """
        Get recent activities across all activity types.

        Args:
            limit (int): Maximum number of activities to return
            activity_types (list): Filter by specific activity types
            date_range (tuple): Start and end date filter (start_date, end_date)

        Returns:
            list: List of activity dictionaries with consistent structure
        """
        activities = []

        # Get collection activities
        if activity_types is None or "collection" in activity_types:
            activities.extend(cls._get_collection_activities(limit, date_range))

        # Get compromise agreement activities
        if activity_types is None or "compromise" in activity_types:
            activities.extend(cls._get_compromise_activities(limit, date_range))

        # Get remedial strategy activities
        if activity_types is None or "strategy" in activity_types:
            activities.extend(cls._get_strategy_activities(limit, date_range))

        # Get delinquency status activities
        if activity_types is None or "delinquency" in activity_types:
            activities.extend(cls._get_delinquency_activities(limit, date_range))

        # Get exposure snapshot activities
        if activity_types is None or "exposure" in activity_types:
            activities.extend(cls._get_exposure_activities(limit, date_range))

        # Sort all activities by date (most recent first)
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        # Limit the total number of activities
        return activities[:limit]

    @classmethod
    def _get_collection_activities(cls, limit, date_range):
        """Get collection activity log entries."""
        queryset = CollectionActivityLog.objects.all()

        if date_range:
            start_date, end_date = date_range
            queryset = queryset.filter(activity_date__range=date_range)

        activities = queryset.order_by("-activity_date", "-activity_id")[:limit]

        return [
            {
                "id": f"collection_{activity.activity_id}",
                "type": "collection",
                "type_display": cls.ACTIVITY_TYPES["collection"],
                "title": f"{activity.get_activity_type_display()} - {activity.account.loan_id}",
                "description": activity.remarks or "No remarks",
                "timestamp": timezone.make_aware(
                    datetime.combine(activity.activity_date, datetime.min.time())
                ),
                "created_by": activity.created_by,
                "loan_id": activity.account.loan_id,
                "borrower_name": activity.account.borrower.full_name,
                "url": f"/account/{activity.account.loan_id}/#collection",
                "icon": "bi-telephone",
                "color": "info",
            }
            for activity in activities
        ]

    @classmethod
    def _get_compromise_activities(cls, limit, date_range):
        """Get compromise agreement activities."""
        queryset = CompromiseAgreement.objects.all()

        if date_range:
            start_date, end_date = date_range
            queryset = queryset.filter(created_at__range=date_range)

        agreements = queryset.order_by("-created_at", "-compromise_id")[:limit]

        activities = []
        for agreement in agreements:
            activities.append(
                {
                    "id": f"compromise_{agreement.compromise_id}_created",
                    "type": "compromise",
                    "type_display": cls.ACTIVITY_TYPES["compromise"],
                    "title": f"Compromise Agreement Created - {agreement.compromise_id}",
                    "description": f"Amount: {agreement.discount_amount}",
                    "timestamp": agreement.created_at,
                    "created_by": agreement.created_by,
                    "loan_id": agreement.account.loan_id,
                    "borrower_name": agreement.account.borrower.full_name,
                    "url": f"/compromise/{agreement.compromise_id}/",
                    "icon": "bi-handshake",
                    "color": "success",
                }
            )

        return activities

    @classmethod
    def _get_strategy_activities(cls, limit, date_range):
        """Get remedial strategy activities."""
        queryset = RemedialStrategy.objects.all()

        if date_range:
            start_date, end_date = date_range
            queryset = queryset.filter(created_at__range=date_range)

        strategies = queryset.order_by("-created_at", "-strategy_id")[:limit]

        activities = []
        for strategy in strategies:
            activities.append(
                {
                    "id": f"strategy_{strategy.strategy_id}_created",
                    "type": "strategy",
                    "type_display": cls.ACTIVITY_TYPES["strategy"],
                    "title": f"{strategy.get_strategy_type_display()} Strategy - {strategy.account.loan_id} - {strategy.strategy_status.lower}",
                    "description": f"Strategy {strategy.strategy_status}",
                    "timestamp": strategy.created_at,
                    "created_by": strategy.created_by,
                    "loan_id": strategy.account.loan_id,
                    "borrower_name": strategy.account.borrower.full_name,
                    "url": f"/account/{strategy.account.loan_id}/#strategy",
                    "icon": "bi-gear",
                    "color": "primary",
                }
            )

        return activities

    @classmethod
    def _get_delinquency_activities(cls, limit, date_range):
        """Get delinquency status change activities."""
        queryset = DelinquencyStatus.objects.all()

        if date_range:
            start_date, end_date = date_range
            queryset = queryset.filter(as_of_date__range=date_range)

        delinquencies = queryset.order_by("-as_of_date", "-delinquency_id")[:limit]

        activities = []
        for delinquency in delinquencies:
            # Check if this is a significant change (classification change or NPL flag)
            if (
                delinquency.classification in ["DOUBTFUL", "LOSS"]
                or delinquency.npl_flag
            ):
                activities.append(
                    {
                        "id": f"delinquency_{delinquency.delinquency_id}",
                        "type": "delinquency",
                        "type_display": cls.ACTIVITY_TYPES["delinquency"],
                        "title": f"Classification Change - {delinquency.account.loan_id}",
                        "description": f"{delinquency.classification} ({delinquency.days_past_due} DPD)",
                        "timestamp": timezone.make_aware(
                            datetime.combine(
                                delinquency.as_of_date, datetime.min.time()
                            )
                        ),
                        "created_by": delinquency.created_by,
                        "loan_id": delinquency.account.loan_id,
                        "borrower_name": delinquency.account.borrower.full_name,
                        "url": f"/account/{delinquency.account.loan_id}/#delinquency",
                        "icon": "bi-exclamation-triangle",
                        "color": "warning"
                        if delinquency.classification == "DOUBTFUL"
                        else "danger",
                    }
                )

        return activities

    @classmethod
    def _get_exposure_activities(cls, limit, date_range):
        """Get significant exposure snapshot activities."""
        from ..models import Exposure

        queryset = Exposure.objects.all()

        if date_range:
            start_date, end_date = date_range
            queryset = queryset.filter(as_of_date__range=date_range)

        exposures = queryset.order_by("-as_of_date", "-exposure_id")[:limit]

        activities = []
        for exposure in exposures:
            # Only include significant exposures (large amounts or high DPD)
            total_exposure = (
                exposure.principal_outstanding
                + exposure.accrued_interest
                + exposure.accrued_penalty
            )

            # Define significant as high amounts (over 1M)
            if total_exposure > 1000000:
                activities.append(
                    {
                        "id": f"exposure_{exposure.exposure_id}",
                        "type": "exposure",
                        "type_display": cls.ACTIVITY_TYPES["exposure"],
                        "title": f"Exposure Snapshot - {exposure.account.loan_id}",
                        "description": f"Total: {total_exposure:,.2f}",
                        "timestamp": timezone.make_aware(
                            datetime.combine(exposure.as_of_date, datetime.min.time())
                        ),
                        "created_by": exposure.created_by,
                        "loan_id": exposure.account.loan_id,
                        "borrower_name": exposure.account.borrower.full_name,
                        "url": f"/account/{exposure.account.loan_id}/#exposure",
                        "icon": "bi-graph-up",
                        "color": "secondary",
                    }
                )

        return activities

    @classmethod
    def get_activity_summary(cls, days=7):
        """
        Get activity summary by type for the specified number of days.

        Args:
            days (int): Number of days to look back

        Returns:
            dict: Activity counts by type
        """
        start_date = timezone.now() - timedelta(days=days)

        # Get all activities for the period
        activities = cls.get_recent_activities(
            limit=1000,  # Large limit to get all activities
            date_range=(start_date, timezone.now()),
        )

        # Count by activity type
        summary = {activity_type: 0 for activity_type in cls.ACTIVITY_TYPES.keys()}

        for activity in activities:
            if activity["type"] in summary:
                summary[activity["type"]] += 1

        return summary

    @classmethod
    def get_activities_by_user(cls, user, limit=20):
        """
        Get recent activities for a specific user.

        Args:
            user: User object
            limit (int): Maximum number of activities to return

        Returns:
            list: List of activity dictionaries
        """
        if not user or not user.is_authenticated:
            return []

        # Get all activities (we'll filter in Python)
        all_activities = cls.get_recent_activities(limit=1000)

        # Filter by user
        user_activities = [
            activity for activity in all_activities if activity["created_by"] == user
        ]

        # Sort by timestamp and limit
        user_activities.sort(key=lambda x: x["timestamp"], reverse=True)

        return user_activities[:limit]
