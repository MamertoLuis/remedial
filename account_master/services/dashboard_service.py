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
    OuterRef,
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
                latest_exposures = Exposure.objects.filter(
                    account=OuterRef("account")
                ).order_by("-as_of_date")

                # Sum the latest exposure amounts (principal outstanding only)
                total_exposure = Exposure.objects.filter(
                    pk=Subquery(latest_exposures.values("pk")[:1])
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
    def get_total_past_due_loans(cls):
        """
        Calculate total past due loans amount.

        Returns:
            Decimal: Total principal outstanding for past due loans
        """
        cache_key = cls.get_cache_key("total_past_due_loans")
        result = cache.get(cache_key)

        if result is None:
            try:
                # Get accounts with PAST_DUE status
                past_due_accounts = LoanAccount.objects.filter(status="PAST_DUE")

                if not past_due_accounts.exists():
                    result = Decimal("0.00")
                    cache.set(cache_key, result, cls.CACHE_TIMEOUT)
                    return result

                # Get the latest exposure for each past due account
                latest_exposures = Exposure.objects.filter(
                    account=OuterRef("account")
                ).order_by("-as_of_date")

                # Sum the latest exposure amounts for past due accounts
                total_past_due = Exposure.objects.filter(
                    pk=Subquery(latest_exposures.values("pk")[:1]),
                    account__status="PAST_DUE",
                ).aggregate(total_past_due=Sum("principal_outstanding"))[
                    "total_past_due"
                ] or Decimal("0.00")

                result = total_past_due
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating total past due loans: {e}")
                result = Decimal("0.00")

        return result

    @classmethod
    def get_total_npl_amount(cls):
        """
        Calculate total NPL amount.

        Returns:
            Decimal: Total principal outstanding for NPL loans
        """
        cache_key = cls.get_cache_key("total_npl_amount")
        result = cache.get(cache_key)

        if result is None:
            try:
                # Get accounts with NPL status
                npl_accounts = LoanAccount.objects.filter(status="NPL")

                if not npl_accounts.exists():
                    result = Decimal("0.00")
                    cache.set(cache_key, result, cls.CACHE_TIMEOUT)
                    return result

                # Get the latest exposure for each NPL account
                latest_exposures = Exposure.objects.filter(
                    account=OuterRef("account")
                ).order_by("-as_of_date")

                # Sum the latest exposure amounts for NPL accounts
                total_npl = Exposure.objects.filter(
                    pk=Subquery(latest_exposures.values("pk")[:1]),
                    account__status="NPL",
                ).aggregate(total_npl=Sum("principal_outstanding"))[
                    "total_npl"
                ] or Decimal("0.00")

                result = total_npl
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating total NPL amount: {e}")
                result = Decimal("0.00")

        return result

    @classmethod
    def get_total_remedial_amount(cls):
        """
        Calculate total amount for accounts under remedial strategies.

        Returns:
            Decimal: Total principal outstanding for accounts with active remedial strategies
        """
        cache_key = cls.get_cache_key("total_remedial_amount")
        result = cache.get(cache_key)

        if result is None:
            try:
                # Get accounts with active remedial strategies
                accounts_with_active_strategies = LoanAccount.objects.filter(
                    remedial_strategies__strategy_status="ACTIVE"
                ).distinct()

                if not accounts_with_active_strategies.exists():
                    result = Decimal("0.00")
                    cache.set(cache_key, result, cls.CACHE_TIMEOUT)
                    return result

                # Get the latest exposure for each account with active strategies
                latest_exposures = Exposure.objects.filter(
                    account=OuterRef("account")
                ).order_by("-as_of_date")

                # Sum the latest exposure amounts for accounts with active strategies
                total_remedial = Exposure.objects.filter(
                    pk=Subquery(latest_exposures.values("pk")[:1]),
                    account__remedial_strategies__strategy_status="ACTIVE",
                ).aggregate(total_remedial=Sum("principal_outstanding"))[
                    "total_remedial"
                ] or Decimal("0.00")

                result = total_remedial
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating total remedial amount: {e}")
                result = Decimal("0.00")

        return result

    @classmethod
    def get_total_legal_amount(cls):
        """
        Calculate total amount for accounts under legal action.

        Returns:
            Decimal: Total principal outstanding for accounts with legal action strategies
        """
        cache_key = cls.get_cache_key("total_legal_amount")
        result = cache.get(cache_key)

        if result is None:
            try:
                # Get accounts with legal action strategies
                accounts_with_legal_strategies = LoanAccount.objects.filter(
                    remedial_strategies__strategy_type="Legal Action",
                    remedial_strategies__strategy_status="ACTIVE",
                ).distinct()

                if not accounts_with_legal_strategies.exists():
                    result = Decimal("0.00")
                    cache.set(cache_key, result, cls.CACHE_TIMEOUT)
                    return result

                # Get the latest exposure for each account with legal strategies
                latest_exposures = Exposure.objects.filter(
                    account=OuterRef("account")
                ).order_by("-as_of_date")

                # Sum the latest exposure amounts for accounts with legal strategies
                total_legal = Exposure.objects.filter(
                    pk=Subquery(latest_exposures.values("pk")[:1]),
                    account__remedial_strategies__strategy_type="Legal Action",
                    account__remedial_strategies__strategy_status="ACTIVE",
                ).aggregate(total_legal=Sum("principal_outstanding"))[
                    "total_legal"
                ] or Decimal("0.00")

                result = total_legal
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating total legal amount: {e}")
                result = Decimal("0.00")

        return result

    @classmethod
    def get_total_written_off_mtd(cls):
        """
        Calculate total written-off amount for current month.

        Returns:
            Decimal: Total principal outstanding for accounts written off this month
        """
        cache_key = cls.get_cache_key("total_written_off_mtd")
        result = cache.get(cache_key)

        if result is None:
            try:
                # Get current month start and end
                now = timezone.now()
                current_month_start = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                current_month_end = (
                    now.replace(day=28) + timezone.timedelta(days=4)
                ).replace(day=1) - timezone.timedelta(seconds=1)

                # Get accounts with WRITEOFF status updated in current month
                written_off_accounts = LoanAccount.objects.filter(
                    status="WRITEOFF",
                    updated_at__gte=current_month_start,
                    updated_at__lte=current_month_end,
                )

                if not written_off_accounts.exists():
                    result = Decimal("0.00")
                    cache.set(cache_key, result, cls.CACHE_TIMEOUT)
                    return result

                # Get the latest exposure for each written-off account
                latest_exposures = Exposure.objects.filter(
                    account=OuterRef("account")
                ).order_by("-as_of_date")

                # Sum the latest exposure amounts for written-off accounts
                total_written_off = Exposure.objects.filter(
                    pk=Subquery(latest_exposures.values("pk")[:1]),
                    account__status="WRITEOFF",
                    account__updated_at__gte=current_month_start,
                    account__updated_at__lte=current_month_end,
                ).aggregate(total_written_off=Sum("principal_outstanding"))[
                    "total_written_off"
                ] or Decimal("0.00")

                result = total_written_off
                cache.set(cache_key, result, cls.CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Error calculating total written-off MTD: {e}")
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
                    # Updated portfolio metrics
                    "total_loan_portfolio": cls.get_total_portfolio_exposure(),
                    "total_past_due_loans": cls.get_total_past_due_loans(),
                    "total_npl": cls.get_total_npl_amount(),
                    "npl_ratio": cls.get_npl_ratio(),
                    "total_remedial": cls.get_total_remedial_amount(),
                    "total_legal": cls.get_total_legal_amount(),
                    "total_written_off_mtd": cls.get_total_written_off_mtd(),
                    # Keep some existing useful metrics
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
            # Updated portfolio metrics
            "total_loan_portfolio": Decimal("0.00"),
            "total_past_due_loans": Decimal("0.00"),
            "total_npl": Decimal("0.00"),
            "npl_ratio": 0.0,
            "total_remedial": Decimal("0.00"),
            "total_legal": Decimal("0.00"),
            "total_written_off_mtd": Decimal("0.00"),
            # Keep some existing useful metrics
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
        try:
            if hasattr(cache, "keys"):
                cache_pattern = f"{cls.CACHE_PREFIX}*"
                keys = cache.keys(cache_pattern)
                if keys:
                    cache.delete_many(keys)
                    logger.info(f"Cleared {len(keys)} dashboard cache entries")
            else:
                cache.clear()
                logger.info(
                    "Cleared all cache entries (backend doesn't support keys())"
                )
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
