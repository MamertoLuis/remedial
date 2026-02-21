from django.db.models import (
    Sum,
    Count,
    Avg,
    Q,
    F,
    ExpressionWrapper,
    DecimalField,
    Max,
    Subquery,
)
from django.db.models.functions import TruncMonth, TruncDay
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
import logging

from ..models import (
    LoanAccount,
    Borrower,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
    CollectionActivityLog,
)
from compromise_agreement.models import CompromiseAgreement, CompromiseInstallment

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service class for calculating dashboard KPIs and metrics.
    Implements caching for expensive calculations and efficient database queries.
    """

    # Cache keys
    CACHE_PREFIX = "dashboard_"
    CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def get_cache_key(cls, method_name, *args):
        """Generate cache key for method calls."""
        return f"{cls.CACHE_PREFIX}{method_name}_{'_'.join(str(arg) for arg in args)}"

    @classmethod
    def get_total_portfolio_exposure(cls):
        """
        Calculate total portfolio exposure from latest exposure snapshots.

        Returns:
            Decimal: Total exposure amount across all loan accounts
        """
        cache_key = cls.get_cache_key("total_portfolio_exposure")
        result = cache.get(cache_key)

        if result is None:
            try:
                # Get the latest exposure for each account
                latest_exposures = (
                    Exposure.objects.filter(as_of_date__isnull=False)
                    .values("account_id")
                    .annotate(latest_date=Max("as_of_date"))
                )

                # Sum the latest exposure amounts (principal outstanding only)
                total_exposure = Exposure.objects.filter(
                    exposure_id__in=Subquery(
                        Exposure.objects.filter(as_of_date__isnull=False)
                        .values("account_id")
                        .annotate(latest_date=Max("as_of_date"))
                        .values("exposure_id")
                    )
                ).aggregate(total_exposure=Sum("principal_outstanding"))[
                    "total_exposure"
                ] or Decimal("0.00")

                result = total_exposure
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating total portfolio exposure: {e}")
                result = Decimal("0.00")

        return result

    @classmethod
    def get_npl_ratio(cls):
        """
        Calculate NPL ratio (Non-Performing Loans ratio).
        NPL = Accounts with status 'NPL'.
        """
        cache_key = cls.get_cache_key("npl_ratio")
        result = cache.get(cache_key)

        if result is None:
            try:
                total_accounts = LoanAccount.objects.exclude(status="CLOSED").count()

                if total_accounts == 0:
                    return 0.0

                npl_accounts = LoanAccount.objects.filter(status="NPL").count()

                npl_ratio = (npl_accounts / total_accounts) * 100
                result = round(float(npl_ratio), 2)
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating NPL ratio: {e}")
                result = 0.0

        return result

    @classmethod
    def get_recovery_rate(cls):
        """
        Calculate recovery rate (recovered amount vs total exposure).
        Uses actual paid amounts from compromise installments.

        Returns:
            float: Recovery rate as percentage
        """
        cache_key = cls.get_cache_key("recovery_rate")
        result = cache.get(cache_key)

        if result is None:
            try:
                total_exposure = cls.get_total_portfolio_exposure()

                if total_exposure == 0:
                    return 0.0

                # Calculate recovered amounts using actual paid installments
                total_recovered = CompromiseInstallment.objects.filter(
                    status="PAID"
                ).aggregate(total_recovered=Sum("amount_paid"))[
                    "total_recovered"
                ] or Decimal("0.00")

                recovery_rate = (total_recovered / total_exposure) * 100
                result = round(float(recovery_rate), 2)
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating recovery rate: {e}")
                result = 0.0

        return result

    @classmethod
    def get_provision_coverage(cls):
        """
        Calculate provision coverage ratio (total provisions vs NPL exposure).

        Returns:
            float: Provision coverage as percentage
        """
        cache_key = cls.get_cache_key("provision_coverage")
        result = cache.get(cache_key)

        if result is None:
            try:
                # Get NPL accounts
                npl_accounts = LoanAccount.objects.filter(status="NPL")
                npl_exposure = Decimal("0.00")

                # Calculate total exposure for NPL accounts from their latest snapshot
                for account in npl_accounts:
                    latest_exposure = account.exposures.order_by("-as_of_date").first()
                    if latest_exposure:
                        npl_exposure += latest_exposure.principal_outstanding

                if npl_exposure == 0:
                    return 0.0

                # Get total provisions from ECL history for currently NPL accounts
                from ..models import ECLProvisionHistory

                total_provisions = ECLProvisionHistory.objects.filter(
                    exposure__account__in=npl_accounts, is_current=True
                ).aggregate(total_provisions=Sum("provision_amount"))[
                    "total_provisions"
                ] or Decimal("0.00")

                provision_coverage = (total_provisions / npl_exposure) * 100
                result = round(float(provision_coverage), 2)
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating provision coverage: {e}")
                result = 0.0

        return result

    @classmethod
    def get_active_strategies_count(cls):
        """
        Get count of active remedial strategies by type.

        Returns:
            dict: Dictionary with strategy types and counts
        """
        cache_key = cls.get_cache_key("active_strategies_count")
        result = cache.get(cache_key)

        if result is None:
            try:
                strategies = (
                    RemedialStrategy.objects.filter(strategy_status="ACTIVE")
                    .values("strategy_type")
                    .annotate(count=Count("strategy_id"))
                )

                result = {item["strategy_type"]: item["count"] for item in strategies}
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error getting active strategies count: {e}")
                result = {}

        return result

    @classmethod
    def get_delinquency_trend(cls, months=6):
        """
        Calculate delinquency trend over specified months.

        Args:
            months (int): Number of months to look back

        Returns:
            list: List of dictionaries with month and average DPD
        """
        cache_key = cls.get_cache_key("delinquency_trend", months)
        result = cache.get(cache_key)

        if result is None:
            try:
                cutoff_date = timezone.now() - timezone.timedelta(days=30 * months)

                # Group by month and calculate average DPD
                monthly_data = (
                    DelinquencyStatus.objects.filter(as_of_date__gte=cutoff_date)
                    .annotate(month=TruncMonth("as_of_date"))
                    .values("month")
                    .annotate(
                        avg_dpd=Avg("days_past_due"), count=Count("delinquency_id")
                    )
                    .order_by("month")
                )

                result = [
                    {
                        "month": item["month"].strftime("%Y-%m"),
                        "avg_dpd": round(float(item["avg_dpd"] or 0), 1),
                        "count": item["count"],
                    }
                    for item in monthly_data
                ]
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating delinquency trend: {e}")
                result = []

        return result

    @classmethod
    def get_portfolio_kpis(cls):
        """
        Get all portfolio KPIs in a single call.

        Returns:
            dict: Dictionary with all portfolio KPIs
        """
        # Use a single cache key for all KPIs to ensure consistency
        cache_key = cls.get_cache_key("portfolio_kpis")
        result = cache.get(cache_key)

        if result is None:
            try:
                result = {
                    "total_portfolio_exposure": cls.get_total_portfolio_exposure(),
                    "npl_ratio": cls.get_npl_ratio(),
                    "recovery_rate": cls.get_recovery_rate(),
                    "provision_coverage": cls.get_provision_coverage(),
                    "active_strategies": cls.get_active_strategies_count(),
                    "delinquency_trend": cls.get_delinquency_trend(),
                    # Additional basic metrics
                    "total_borrowers": Borrower.objects.count(),
                    "total_accounts": LoanAccount.objects.count(),
                    "total_compromise_agreements": CompromiseAgreement.objects.count(),
                    # Recent activity counts
                    "recent_activities": CollectionActivityLog.objects.filter(
                        activity_date__gte=timezone.now() - timezone.timedelta(days=7)
                    ).count(),
                    # Active compromise agreements
                    "active_compromise_agreements": CompromiseAgreement.objects.filter(
                        status="ACTIVE"
                    ).count(),
                }
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error getting portfolio KPIs: {e}")
                result = cls._get_default_kpis()

        return result

    @classmethod
    def _get_default_kpis(cls):
        """Return default KPI values in case of errors."""
        return {
            "total_portfolio_exposure": Decimal("0.00"),
            "npl_ratio": 0.0,
            "recovery_rate": 0.0,
            "provision_coverage": 0.0,
            "active_strategies": {},
            "delinquency_trend": [],
            "total_borrowers": 0,
            "total_accounts": 0,
            "total_compromise_agreements": 0,
            "recent_activities": 0,
            "active_compromise_agreements": 0,
        }

    @classmethod
    def clear_cache(cls):
        """Clear all dashboard cache."""
        cache_pattern = f"{cls.CACHE_PREFIX}*"
        keys = cache.keys(cache_pattern)
        cache.delete_many(keys)
        logger.info(f"Cleared {len(keys)} dashboard cache entries")
