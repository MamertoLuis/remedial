from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, Max, Subquery, OuterRef, Min, F
from django.db.models.functions import Coalesce
from decimal import Decimal
from account_master.models import (
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
)


def loan_portfolio_breakdown(request):
    # Get the latest as_of_date from Exposure
    latest_date = (
        Exposure.objects.order_by("-as_of_date")
        .values_list("as_of_date", flat=True)
        .first()
    )

    # Subquery to get the latest principal_outstanding for each LoanAccount
    latest_exposure_subquery = Subquery(
        Exposure.objects.filter(account=OuterRef("loan_id"))
        .order_by("-as_of_date")
        .values("principal_outstanding")[:1]
    )

    loan_accounts_with_latest_balance = LoanAccount.objects.annotate(
        latest_principal_outstanding=Coalesce(latest_exposure_subquery, Decimal(0))
    )

    total_portfolio_balance = loan_accounts_with_latest_balance.aggregate(
        total_balance=Sum("latest_principal_outstanding")
    )["total_balance"]

    # Portfolio by Loan Type
    portfolio_by_loan_type = (
        loan_accounts_with_latest_balance.values("loan_type")
        .annotate(balance=Sum("latest_principal_outstanding"))
        .order_by("loan_type")
    )

    for item in portfolio_by_loan_type:
        item["percentage"] = (
            (item["balance"] / total_portfolio_balance * 100)
            if total_portfolio_balance
            else Decimal(0)
        )

    # Portfolio by Status
    portfolio_by_status = (
        loan_accounts_with_latest_balance.values("status")
        .annotate(balance=Sum("latest_principal_outstanding"))
        .order_by("status")
    )

    for item in portfolio_by_status:
        item["percentage"] = (
            (item["balance"] / total_portfolio_balance * 100)
            if total_portfolio_balance
            else Decimal(0)
        )

    context = {
        "title": "Loan Portfolio Breakdown",
        "portfolio_by_loan_type": portfolio_by_loan_type,
        "portfolio_by_status": portfolio_by_status,
        "total_portfolio_balance": total_portfolio_balance,
        "report_date": latest_date,
    }
    return render(request, "reporting/loan_portfolio_breakdown.html", context)


def past_due_aging_summary(request):
    # Get the latest as_of_date from Exposure
    latest_date = (
        Exposure.objects.order_by("-as_of_date")
        .values_list("as_of_date", flat=True)
        .first()
    )

    # Subquery to get the latest principal_outstanding for each LoanAccount
    latest_exposure_subquery = Subquery(
        Exposure.objects.filter(account=OuterRef("loan_id"))
        .order_by("-as_of_date")
        .values("principal_outstanding")[:1]
    )

    past_due_accounts = LoanAccount.objects.filter(status="PAST_DUE").annotate(
        current_exposure=Coalesce(latest_exposure_subquery, Decimal(0))
    )

    aging_summary = {}

    for account in past_due_accounts:
        officer = account.account_officer_id if account.account_officer_id else "N/A"
        if officer not in aging_summary:
            aging_summary[officer] = {
                "1-30": {"amount": Decimal(0), "accounts": 0},
                "31-60": {"amount": Decimal(0), "accounts": 0},
                "61-90": {"amount": Decimal(0), "accounts": 0},
                "91-120": {"amount": Decimal(0), "accounts": 0},
                "121-180": {"amount": Decimal(0), "accounts": 0},
                "181-360": {"amount": Decimal(0), "accounts": 0},
                "Over 360": {"amount": Decimal(0), "accounts": 0},
            }

        # Assuming the latest delinquency status reflects the current aging
        latest_delinquency = account.delinquency_statuses.order_by(
            "-as_of_date"
        ).first()
        if latest_delinquency and latest_delinquency.aging_bucket:
            bucket = latest_delinquency.aging_bucket
            if bucket in aging_summary[officer]:
                aging_summary[officer][bucket]["amount"] += account.current_exposure
                aging_summary[officer][bucket]["accounts"] += 1

    # Convert to a list of dictionaries for easier template rendering
    report_data = []
    for officer, buckets in aging_summary.items():
        officer_total_amount = sum(b["amount"] for b in buckets.values())
        officer_total_accounts = sum(b["accounts"] for b in buckets.values())
        report_data.append(
            {
                "officer": officer,
                "buckets": buckets,
                "officer_total_amount": officer_total_amount,
                "officer_total_accounts": officer_total_accounts,
            }
        )

    # Sort officers by name
    report_data.sort(key=lambda x: x["officer"])

    context = {
        "title": "Past Due Aging Summary",
        "report_data": report_data,
        "aging_buckets_order": [
            "1-30",
            "31-60",
            "61-90",
            "91-120",
            "121-180",
            "181-360",
            "Over 360",
        ],
        "report_date": latest_date,
    }
    return render(request, "reporting/past_due_aging_summary.html", context)


def npl_portfolio_analysis(request):
    # Get the latest as_of_date from Exposure
    latest_date = (
        Exposure.objects.order_by("-as_of_date")
        .values_list("as_of_date", flat=True)
        .first()
    )

    npl_accounts = (
        LoanAccount.objects.filter(delinquency_statuses__npl_flag=True)
        .exclude(exposures__principal_outstanding=Decimal("1"))
        .distinct()
        .prefetch_related("exposures", "remedial_strategies")
        .order_by("loan_id")
    )

    report_data = []
    npl_by_strategy = {}

    for account in npl_accounts:
        latest_exposure = account.exposures.order_by("-as_of_date").first()
        latest_delinquency = account.delinquency_statuses.order_by(
            "-as_of_date"
        ).first()
        active_strategy = account.remedial_strategies.filter(
            strategy_status="ACTIVE"
        ).first()

        if latest_exposure and latest_delinquency:
            balance = latest_exposure.principal_outstanding
            days_past_due = latest_delinquency.days_past_due
            strategy_type = (
                active_strategy.strategy_type
                if active_strategy
                else "No Active Strategy"
            )

            report_data.append(
                {
                    "borrower": account.borrower.full_name,
                    "loan_id": account.loan_id,
                    "balance": balance,
                    "days_past_due": days_past_due,
                    "collateral": account.loan_security,  # Assuming loan_security indicates collateral
                    "strategy": strategy_type,
                    "officer": account.account_officer_id,
                }
            )

            # Summarize by strategy
            if strategy_type not in npl_by_strategy:
                npl_by_strategy[strategy_type] = {"balance": Decimal(0), "accounts": 0}
            npl_by_strategy[strategy_type]["balance"] += balance
            npl_by_strategy[strategy_type]["accounts"] += 1

    # Sort npl_by_strategy for consistent display
    npl_by_strategy_list = sorted(
        [
            {"strategy": k, "balance": v["balance"], "accounts": v["accounts"]}
            for k, v in npl_by_strategy.items()
        ],
        key=lambda x: x["strategy"],
    )

    context = {
        "title": "Non-Performing Loans Report",
        "report_data": report_data,
        "npl_by_strategy": npl_by_strategy_list,
        "report_date": latest_date,
    }

    return render(request, "reporting/npl_portfolio_analysis.html", context)


def top_20_npl_accounts(request):
    # Get the latest as_of_date from Exposure
    latest_date = (
        Exposure.objects.order_by("-as_of_date")
        .values_list("as_of_date", flat=True)
        .first()
    )

    latest_exposure_subquery = Subquery(
        Exposure.objects.filter(account=OuterRef("loan_id"))
        .order_by("-as_of_date")
        .values("principal_outstanding")[:1]
    )

    top_npl_accounts = (
        LoanAccount.objects.filter(delinquency_statuses__npl_flag=True)
        .exclude(exposures__principal_outstanding=Decimal("1"))
        .annotate(
            latest_principal_outstanding=Coalesce(latest_exposure_subquery, Decimal(0))
        )
        .order_by("-latest_principal_outstanding")
        .distinct()
        .prefetch_related("exposures", "remedial_strategies", "borrower")
    )[:20]

    report_data = []
    for account in top_npl_accounts:
        latest_exposure = account.exposures.order_by("-as_of_date").first()
        latest_delinquency = account.delinquency_statuses.order_by(
            "-as_of_date"
        ).first()
        active_strategy = account.remedial_strategies.filter(
            strategy_status="ACTIVE"
        ).first()

        if latest_exposure and latest_delinquency:
            balance = latest_exposure.principal_outstanding
            days_past_due = latest_delinquency.days_past_due
            strategy_type = (
                active_strategy.strategy_type
                if active_strategy
                else "No Active Strategy"
            )

            report_data.append(
                {
                    "borrower": account.borrower.full_name,
                    "loan_id": account.loan_id,
                    "balance": balance,
                    "days_past_due": days_past_due,
                    "collateral": account.loan_security,
                    "strategy": strategy_type,
                    "officer": account.account_officer_id,
                }
            )

    context = {
        "title": "Top 20 Non-Performing Loans",
        "report_data": report_data,
        "report_date": latest_date,
    }
    return render(request, "reporting/top_20_npl_accounts.html", context)


def loan_officer_performance_summary(request):
    # Get the latest as_of_date from Exposure for report date
    latest_date = (
        Exposure.objects.order_by("-as_of_date")
        .values_list("as_of_date", flat=True)
        .first()
    )

    # Get current month start and end dates
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_end = now

    # Get unique account officers from LoanAccount
    officers = (
        LoanAccount.objects.exclude(account_officer_id="")
        .values_list("account_officer_id", flat=True)
        .distinct()
        .order_by("account_officer_id")
    )

    # Subquery to get the latest principal_outstanding for each LoanAccount
    latest_exposure_subquery = Subquery(
        Exposure.objects.filter(account=OuterRef("loan_id"))
        .order_by("-as_of_date")
        .values("principal_outstanding")[:1]
    )

    report_data = []

    for officer_id in officers:
        # Get accounts assigned to this officer
        accounts = LoanAccount.objects.filter(account_officer_id=officer_id)

        # Accounts assigned count
        accounts_assigned = accounts.count()

        if accounts_assigned == 0:
            continue  # Skip officers with no accounts

        # Portfolio balance
        accounts_with_exposure = accounts.annotate(
            latest_principal_outstanding=Coalesce(latest_exposure_subquery, Decimal(0))
        )
        portfolio_balance = accounts_with_exposure.aggregate(
            total=Sum("latest_principal_outstanding")
        )["total"] or Decimal(0)

        # Past due balance
        past_due_balance = accounts_with_exposure.filter(status="PAST_DUE").aggregate(
            total=Sum("latest_principal_outstanding")
        )["total"] or Decimal(0)

        # NPL balance
        npl_balance = accounts_with_exposure.filter(status="NPL").aggregate(
            total=Sum("latest_principal_outstanding")
        )["total"] or Decimal(0)

        # Collected amount (current month)
        # Get account IDs for this officer
        officer_account_ids = accounts.values_list("loan_id", flat=True)

        # Get shouldbepay and actualpay for each account in current month
        monthly_payments = (
            Exposure.objects.filter(
                account_id__in=officer_account_ids,
                as_of_date__gte=current_month_start,
                as_of_date__lte=current_month_end,
                shouldbepay__isnull=False,
            )
            .values("account_id")
            .annotate(
                total_shouldbepay=Sum("shouldbepay"),
                total_actualpay=Sum("actualpay"),
            )
        )

        total_shouldbepay = Decimal(0)
        total_actualpay = Decimal(0)

        for payment in monthly_payments:
            total_shouldbepay += payment["total_shouldbepay"] or Decimal(0)
            total_actualpay += payment["total_actualpay"] or Decimal(0)

        # Collection rate using shouldbepay and actualpay
        collection_rate = (
            (total_actualpay / total_shouldbepay * 100)
            if total_shouldbepay > 0
            else Decimal(0)
        )

        report_data.append(
            {
                "officer": officer_id,
                "accounts_assigned": accounts_assigned,
                "portfolio_balance": portfolio_balance,
                "past_due_balance": past_due_balance,
                "npl_balance": npl_balance,
                "shouldbepay": total_shouldbepay,
                "actualpay": total_actualpay,
                "collection_rate": collection_rate,
            }
        )

    # Calculate totals
    total_accounts = sum(item["accounts_assigned"] for item in report_data)
    total_portfolio_balance = sum(item["portfolio_balance"] for item in report_data)
    total_past_due_balance = sum(item["past_due_balance"] for item in report_data)
    total_npl_balance = sum(item["npl_balance"] for item in report_data)
    total_shouldbepay_all = sum(item["shouldbepay"] for item in report_data)
    total_actualpay_all = sum(item["actualpay"] for item in report_data)
    overall_collection_rate = (
        (total_actualpay_all / total_shouldbepay_all * 100)
        if total_shouldbepay_all > 0
        else Decimal(0)
    )

    context = {
        "title": "Loan Officer Performance Summary",
        "report_data": report_data,
        "report_date": latest_date,
        "current_month": current_month_start.strftime("%B %Y"),
        "total_accounts": total_accounts,
        "total_portfolio_balance": total_portfolio_balance,
        "total_past_due_balance": total_past_due_balance,
        "total_npl_balance": total_npl_balance,
        "total_shouldbepay": total_shouldbepay_all,
        "total_actualpay": total_actualpay_all,
        "overall_collection_rate": overall_collection_rate,
    }
    return render(request, "reporting/loan_officer_performance_summary.html", context)


def reports_index(request):
    context = {
        "title": "Reports Index",
        "reports": [
            {
                "name": "Loan Portfolio Breakdown",
                "url_name": "reporting:loan_portfolio_breakdown",
            },
            {
                "name": "Past Due Aging Summary",
                "url_name": "reporting:past_due_aging_summary",
            },
            {
                "name": "NPL Portfolio Analysis",
                "url_name": "reporting:npl_portfolio_analysis",
            },
            {
                "name": "Top 20 Non-Performing Loans",
                "url_name": "reporting:top_20_npl_accounts",
            },
            {
                "name": "Loan Officer Performance Summary",
                "url_name": "reporting:loan_officer_performance_summary",
            },
        ],
    }
    return render(request, "reporting/reports_index.html", context)
