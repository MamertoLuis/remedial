from django.db.models import Q, Count, Sum, Max
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import timedelta, date
import logging

from ..models import (
    Alert,
    AlertRule,
    AlertLog,
    LoanAccount,
    DelinquencyStatus,
    Exposure,
    CollectionActivityLog,
)
from compromise_agreement.models import CompromiseAgreement
from ..services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

User = get_user_model()


class AlertService:
    """
    Service class for managing alerts, notifications, and automated alert generation.
    Provides centralized alert creation, management, and rule evaluation.
    """

    # Cache keys
    CACHE_PREFIX = "alert_"
    CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def get_cache_key(cls, method_name, *args):
        """Generate cache key for method calls."""
        return f"{cls.CACHE_PREFIX}{method_name}_{'_'.join(str(arg) for arg in args)}"

    @classmethod
    def create_alert(
        cls,
        alert_type,
        title,
        message,
        entity_type,
        entity_id=None,
        severity="MEDIUM",
        due_date=None,
        created_by=None,
        assigned_to=None,
        metadata=None,
    ):
        """
        Create a new alert.

        Args:
            alert_type (str): Type of alert (CRITICAL, WARNING, INFO, SUCCESS)
            title (str): Alert title
            message (str): Alert message
            entity_type (str): Type of related entity
            entity_id (str, optional): ID of related entity
            severity (str): Alert severity (HIGH, MEDIUM, LOW)
            due_date (date, optional): Due date for action
            created_by (User, optional): User who created the alert
            assigned_to (User, optional): User assigned to the alert
            metadata (dict, optional): Additional alert data

        Returns:
            Alert: Created alert instance
        """
        try:
            alert = Alert.objects.create(
                alert_type=alert_type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
                severity=severity,
                due_date=due_date,
                created_by=created_by,
                assigned_to=assigned_to,
                metadata=metadata or {},
            )

            # Send notifications
            cls._send_alert_notifications(alert)

            logger.info(f"Alert created: {alert.title} (ID: {alert.alert_id})")
            return alert

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            raise

    @classmethod
    def get_active_alerts(cls, user=None, limit=50):
        """
        Get active (unresolved) alerts.

        Args:
            user (User, optional): Filter alerts for specific user
            limit (int): Maximum number of alerts to return

        Returns:
            QuerySet: Active alerts
        """
        cache_key = cls.get_cache_key(
            "active_alerts", user.id if user else "all", limit
        )
        result = cache.get(cache_key)

        if result is None:
            try:
                queryset = Alert.objects.filter(
                    status__in=[Alert.Status.NEW, Alert.Status.ACKNOWLEDGED]
                ).exclude(expires_at__lt=timezone.now())

                if user:
                    queryset = queryset.filter(
                        Q(assigned_to=user) | Q(assigned_to__isnull=True)
                    )

                result = queryset.select_related("created_by", "assigned_to").order_by(
                    "-severity", "-created_at"
                )[:limit]

                cache.set(cache_key, list(result), cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error getting active alerts: {e}")
                result = Alert.objects.none()

        return result

    @classmethod
    def get_alerts_by_type(cls, alert_type, user=None):
        """
        Get alerts by type.

        Args:
            alert_type (str): Alert type to filter
            user (User, optional): Filter alerts for specific user

        Returns:
            QuerySet: Alerts of specified type
        """
        queryset = Alert.objects.filter(alert_type=alert_type)

        if user:
            queryset = queryset.filter(
                Q(assigned_to=user) | Q(assigned_to__isnull=True)
            )

        return queryset.order_by("-created_at")

    @classmethod
    def get_alerts_for_user(cls, user, include_resolved=False):
        """
        Get alerts for a specific user.

        Args:
            user (User): User to get alerts for
            include_resolved (bool): Include resolved alerts

        Returns:
            QuerySet: User's alerts
        """
        queryset = Alert.objects.filter(
            Q(assigned_to=user) | Q(assigned_to__isnull=True)
        )

        if not include_resolved:
            queryset = queryset.exclude(
                status__in=[Alert.Status.RESOLVED, Alert.Status.DISMISSED]
            )

        return queryset.select_related("created_by").order_by("-created_at")

    @classmethod
    def get_alert_counts(cls, user=None):
        """
        Get alert counts by type and severity.

        Args:
            user (User, optional): Filter counts for specific user

        Returns:
            dict: Alert counts
        """
        cache_key = cls.get_cache_key("alert_counts", user.id if user else "all")
        result = cache.get(cache_key)

        if result is None:
            try:
                queryset = Alert.objects.exclude(
                    status__in=[Alert.Status.RESOLVED, Alert.Status.DISMISSED]
                ).exclude(expires_at__lt=timezone.now())

                if user:
                    queryset = queryset.filter(
                        Q(assigned_to=user) | Q(assigned_to__isnull=True)
                    )

                counts = queryset.aggregate(
                    total_critical=Count("alert_id", filter=Q(alert_type="CRITICAL")),
                    total_warning=Count("alert_id", filter=Q(alert_type="WARNING")),
                    total_info=Count("alert_id", filter=Q(alert_type="INFO")),
                    total_high=Count("alert_id", filter=Q(severity="HIGH")),
                    total_medium=Count("alert_id", filter=Q(severity="MEDIUM")),
                    total_low=Count("alert_id", filter=Q(severity="LOW")),
                    total_overdue=Count(
                        "alert_id",
                        filter=Q(
                            due_date__lt=timezone.now().date(),
                            status__in=["NEW", "ACKNOWLEDGED"],
                        ),
                    ),
                )

                total_count = (
                    counts["total_critical"]
                    + counts["total_warning"]
                    + counts["total_info"]
                )

                result = {
                    "total": total_count,
                    "critical": counts["total_critical"],
                    "warning": counts["total_warning"],
                    "info": counts["total_info"],
                    "high_severity": counts["total_high"],
                    "medium_severity": counts["total_medium"],
                    "low_severity": counts["total_low"],
                    "new": queryset.filter(status="NEW").count(),
                    "total_overdue": counts["total_overdue"],
                }
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error getting alert counts: {e}")
                result = {
                    "total": 0,
                    "total_critical": 0,
                    "total_warning": 0,
                    "total_info": 0,
                    "total_high": 0,
                    "total_medium": 0,
                    "total_low": 0,
                    "total_overdue": 0,
                }

        return result

    @classmethod
    def acknowledge_alert(cls, alert_id, user):
        """
        Acknowledge an alert.

        Args:
            alert_id (int): ID of alert to acknowledge
            user (User): User acknowledging the alert

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            alert = Alert.objects.get(alert_id=alert_id)

            if alert.acknowledge(user):
                cls._clear_alert_cache()
                logger.info(f"Alert acknowledged: {alert.title} by {user}")
                return True

            return False

        except Alert.DoesNotExist:
            logger.warning(f"Alert not found for acknowledgement: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False

    @classmethod
    def resolve_alert(cls, alert_id, user, resolution_notes=""):
        """
        Resolve an alert.

        Args:
            alert_id (int): ID of alert to resolve
            user (User): User resolving the alert
            resolution_notes (str): Optional resolution notes

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            alert = Alert.objects.get(alert_id=alert_id)

            if alert.resolve(user, resolution_notes):
                cls._clear_alert_cache()
                logger.info(f"Alert resolved: {alert.title} by {user}")
                return True

            return False

        except Alert.DoesNotExist:
            logger.warning(f"Alert not found for resolution: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False

    @classmethod
    def dismiss_alert(cls, alert_id, user, reason=""):
        """
        Dismiss an alert.

        Args:
            alert_id (int): ID of alert to dismiss
            user (User): User dismissing the alert
            reason (str): Reason for dismissal

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            alert = Alert.objects.get(alert_id=alert_id)

            if alert.dismiss(user, reason):
                cls._clear_alert_cache()
                logger.info(f"Alert dismissed: {alert.title} by {user}")
                return True

            return False

        except Alert.DoesNotExist:
            logger.warning(f"Alert not found for dismissal: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"Error dismissing alert: {e}")
            return False

    @classmethod
    def check_alert_rules(cls):
        """
        Check all active alert rules and create alerts if conditions are met.

        Returns:
            list: List of created alerts
        """
        logger.info("Starting alert rule evaluation")

        all_alerts = []

        try:
            active_rules = AlertRule.objects.filter(is_active=True)
            alerts_created = 0

            for rule in active_rules:
                try:
                    alerts = cls._evaluate_alert_rule(rule)
                    all_alerts.extend(alerts)
                    alerts_created += len(alerts)
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.name}: {e}")

            cls._clear_alert_cache()
            logger.info(
                f"Alert rule evaluation completed. Created {alerts_created} alerts."
            )

            return all_alerts

        except Exception as e:
            logger.error(f"Error in alert rule evaluation: {e}")
            return []

    @classmethod
    def _evaluate_alert_rule(cls, rule):
        """
        Evaluate a single alert rule and create alerts if conditions are met.

        Args:
            rule (AlertRule): Rule to evaluate

        Returns:
            list: Created alerts
        """
        alerts = []

        try:
            if rule.rule_type == AlertRule.RuleType.DPD_THRESHOLD:
                alerts.extend(cls._check_dpd_thresholds(rule))

            elif rule.rule_type == AlertRule.RuleType.EXPOSURE_LIMIT:
                alerts.extend(cls._check_exposure_limits(rule))

            elif rule.rule_type == AlertRule.RuleType.STATUS_CHANGE:
                alerts.extend(cls._check_status_changes(rule))

            elif rule.rule_type == AlertRule.RuleType.AGREEMENT_DEADLINE:
                alerts.extend(cls._check_agreement_deadlines(rule))

            elif rule.rule_type == AlertRule.RuleType.COLLECTION_INACTIVITY:
                alerts.extend(cls._check_collection_inactivity(rule))

            elif rule.rule_type == AlertRule.RuleType.NPL_RATIO:
                alerts.extend(cls._check_npl_ratio(rule))

            elif rule.rule_type == AlertRule.RuleType.PROVISION_COVERAGE:
                alerts.extend(cls._check_provision_coverage(rule))

        except Exception as e:
            logger.error(f"Error evaluating rule {rule.name}: {e}")

        return alerts

    @classmethod
    def _check_dpd_thresholds(cls, rule):
        """Check for accounts exceeding DPD thresholds."""
        alerts = []

        # Get accounts with high DPD
        high_dpd_accounts = DelinquencyStatus.objects.filter(
            days_past_due__gte=rule.condition_value,
            as_of_date__gte=timezone.now() - timedelta(days=30),
        ).select_related("account", "account__borrower")

        for delinquency in high_dpd_accounts:
            # Check if alert already exists for this condition
            existing_alert = Alert.objects.filter(
                entity_type=Alert.EntityType.DELINQUENCY_STATUS,
                entity_id=str(delinquency.delinquency_id),
                status__in=[Alert.Status.NEW, Alert.Status.ACKNOWLEDGED],
            ).first()

            if not existing_alert:
                title = f"High DPD Alert - {delinquency.account.loan_id}"
                message = f"Account has {delinquency.days_past_due} days past due, exceeding threshold of {rule.condition_value}."

                alert = rule.trigger_alert(
                    entity_type=Alert.EntityType.DELINQUENCY_STATUS,
                    entity_id=str(delinquency.delinquency_id),
                    title=title,
                    message=message,
                    metadata={
                        "dpd": delinquency.days_past_due,
                        "threshold": float(rule.condition_value),
                    },
                )

                if alert:
                    alerts.append(alert)

        return alerts

    @classmethod
    def _check_exposure_limits(cls, rule):
        """Check for accounts exceeding exposure limits."""
        alerts = []

        # Get current exposure data
        high_exposure_accounts = Exposure.objects.filter(
            as_of_date__gte=timezone.now() - timedelta(days=30)
        ).select_related("account", "account__borrower")

        for exposure in high_exposure_accounts:
            total_exposure = (
                exposure.principal_outstanding
                + exposure.accrued_interest
                + exposure.accrued_penalty
            )

            if rule.evaluate_condition(total_exposure):
                # Check if alert already exists
                existing_alert = Alert.objects.filter(
                    entity_type=Alert.EntityType.EXPOSURE,
                    entity_id=str(exposure.exposure_id),
                    status__in=["NEW", "ACKNOWLEDGED"],
                ).first()

                if not existing_alert:
                    title = f"High Exposure Alert - {exposure.account.loan_id}"
                    message = f"Account exposure of {total_exposure:,.2f} exceeds threshold of {rule.condition_value:,.2f}."

                    alert = rule.trigger_alert(
                        entity_type=Alert.EntityType.EXPOSURE,
                        entity_id=str(exposure.exposure_id),
                        title=title,
                        message=message,
                        metadata={
                            "exposure": float(total_exposure),
                            "threshold": float(rule.condition_value),
                        },
                    )

                    if alert:
                        alerts.append(alert)

        return alerts

    @classmethod
    def _check_status_changes(cls, rule):
        """Check for significant status changes."""
        alerts = []

        # Get recent status changes to problematic classifications
        recent_changes = DelinquencyStatus.objects.filter(
            classification__in=["SS", "D", "L"],  # Substandard, Doubtful, Loss
            as_of_date__gte=timezone.now() - timedelta(days=7),
        ).select_related("account", "account__borrower")

        for delinquency in recent_changes:
            # Check if alert already exists for this change
            existing_alert = Alert.objects.filter(
                entity_type=Alert.EntityType.DELINQUENCY_STATUS,
                entity_id=str(delinquency.delinquency_id),
                status__in=["NEW", "ACKNOWLEDGED"],
                created_at__gte=timezone.now() - timedelta(hours=24),
            ).first()

            if not existing_alert:
                title = f"Classification Change Alert - {delinquency.account.loan_id}"
                message = f"Account classification changed to {delinquency.get_classification_display()} ({delinquency.days_past_due} DPD)."

                alert = rule.trigger_alert(
                    entity_type=Alert.EntityType.DELINQUENCY_STATUS,
                    entity_id=str(delinquency.delinquency_id),
                    title=title,
                    message=message,
                    metadata={
                        "classification": delinquency.classification,
                        "dpd": delinquency.days_past_due,
                    },
                )

                if alert:
                    alerts.append(alert)

        return alerts

    @classmethod
    def _check_agreement_deadlines(cls, rule):
        """Check for compromise agreements approaching deadline."""
        alerts = []

        # Get active agreements with approaching deadlines
        upcoming_agreements = CompromiseAgreement.objects.filter(
            status="ACTIVE",
            first_payment_date__lte=timezone.now().date()
            + timedelta(days=int(rule.condition_value)),
        ).select_related("account", "account__borrower")

        for agreement in upcoming_agreements:
            # Check if alert already exists
            existing_alert = Alert.objects.filter(
                entity_type=Alert.EntityType.COMPROmise_AGREEMENT,
                entity_id=str(agreement.compromise_id),
                status__in=["NEW", "ACKNOWLEDGED"],
            ).first()

            if not existing_alert:
                title = f"Agreement Deadline Alert - {agreement.agreement_no}"
                message = f"Compromise agreement first payment due on {agreement.first_payment_date}."

                alert = rule.trigger_alert(
                    entity_type=Alert.EntityType.COMPROmise_AGREEMENT,
                    entity_id=str(agreement.compromise_id),
                    title=title,
                    message=message,
                    metadata={"due_date": agreement.first_payment_date.isoformat()},
                )

                if alert:
                    alerts.append(alert)

        return alerts

    @classmethod
    def _check_collection_inactivity(cls, rule):
        """Check for accounts with no recent collection activity."""
        alerts = []

        # Find accounts with no activity in specified days
        cutoff_date = timezone.now() - timedelta(days=int(rule.condition_value))
        inactive_accounts = (
            LoanAccount.objects.annotate(
                last_activity=Max("collection_activities__activity_date")
            )
            .filter(Q(last_activity__lt=cutoff_date) | Q(last_activity__isnull=True))
            .select_related("borrower")
        )

        for account in inactive_accounts:
            # Check if alert already exists
            existing_alert = Alert.objects.filter(
                entity_type=Alert.EntityType.ACCOUNT,
                entity_id=account.loan_id,
                status__in=["NEW", "ACKNOWLEDGED"],
            ).first()

            if not existing_alert:
                title = f"Collection Inactivity Alert - {account.loan_id}"
                message = (
                    f"No collection activity for {int(rule.condition_value)} days."
                )

                alert = rule.trigger_alert(
                    entity_type=Alert.EntityType.ACCOUNT,
                    entity_id=account.loan_id,
                    title=title,
                    message=message,
                    metadata={"days_inactive": int(rule.condition_value)},
                )

                if alert:
                    alerts.append(alert)

        return alerts

    @classmethod
    def _check_npl_ratio(cls, rule):
        """Check for NPL ratio exceeding threshold."""
        alerts = []

        try:
            npl_ratio = DashboardService.get_npl_ratio()

            if rule.evaluate_condition(npl_ratio):
                # Check if alert already exists recently
                existing_alert = Alert.objects.filter(
                    entity_type=Alert.EntityType.SYSTEM,
                    alert_type=rule.alert_type,
                    status__in=["NEW", "ACKNOWLEDGED"],
                    created_at__gte=timezone.now() - timedelta(hours=24),
                ).first()

                if not existing_alert:
                    title = f"NPL Ratio Alert - {npl_ratio:.1f}%"
                    message = f"Portfolio NPL ratio of {npl_ratio:.1f}% exceeds threshold of {rule.condition_value:.1f}%."

                    alert = rule.trigger_alert(
                        entity_type=Alert.EntityType.SYSTEM,
                        entity_id=None,
                        title=title,
                        message=message,
                        metadata={
                            "npl_ratio": npl_ratio,
                            "threshold": float(rule.condition_value),
                        },
                    )

                    if alert:
                        alerts.append(alert)

        except Exception as e:
            logger.error(f"Error checking NPL ratio: {e}")

        return alerts

    @classmethod
    def _check_provision_coverage(cls, rule):
        """Check for provision coverage below threshold."""
        alerts = []

        try:
            provision_coverage = DashboardService.get_provision_coverage()

            if rule.comparison_operator in ["<", "<="]:
                # We want to alert when coverage is below threshold
                if rule.evaluate_condition(provision_coverage):
                    # Check if alert already exists recently
                    existing_alert = Alert.objects.filter(
                        entity_type=Alert.EntityType.SYSTEM,
                        alert_type=rule.alert_type,
                        status__in=["NEW", "ACKNOWLEDGED"],
                        created_at__gte=timezone.now() - timedelta(hours=24),
                    ).first()

                    if not existing_alert:
                        title = f"Provision Coverage Alert - {provision_coverage:.1f}%"
                        message = f"Portfolio provision coverage of {provision_coverage:.1f}% is below threshold of {rule.condition_value:.1f}%."

                        alert = rule.trigger_alert(
                            entity_type=Alert.EntityType.SYSTEM,
                            entity_id=None,
                            title=title,
                            message=message,
                            metadata={
                                "provision_coverage": provision_coverage,
                                "threshold": float(rule.condition_value),
                            },
                        )

                        if alert:
                            alerts.append(alert)

        except Exception as e:
            logger.error(f"Error checking provision coverage: {e}")

        return alerts

    @classmethod
    def _send_alert_notifications(cls, alert):
        """Send notifications for an alert."""
        try:
            # In-app notification is always sent by creating the alert
            # Additional notification channels can be implemented here
            # such as email, SMS, etc.

            logger.debug(f"Notifications sent for alert: {alert.title}")

        except Exception as e:
            logger.error(f"Error sending alert notifications: {e}")

    @classmethod
    def _clear_alert_cache(cls):
        """Clear alert-related cache entries."""
        try:
            # In test environment, just clear specific keys we know about
            cache.delete("alert_counts:global")
            cache.delete("alert_counts:all")
            logger.debug("Cleared alert cache entries")
        except Exception as e:
            logger.error(f"Error clearing alert cache: {e}")

    @classmethod
    def cleanup_expired_alerts(cls, days=30):
        """
        Clean up expired and old resolved alerts.

        Args:
            days (int): Age in days to keep resolved alerts
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days)

            # Delete expired alerts
            expired_count = Alert.objects.filter(
                expires_at__lt=timezone.now(), status__in=["NEW", "ACKNOWLEDGED"]
            ).delete()[0]

            # Delete old resolved alerts
            resolved_count = Alert.objects.filter(
                status__in=["RESOLVED", "DISMISSED"], created_at__lt=cutoff_date
            ).delete()[0]

            logger.info(
                f"Cleaned up {expired_count} expired and {resolved_count} old resolved alerts"
            )

        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}")
