from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth import get_user_model
from account_master.services.dashboard_service import DashboardService
from account_master.services.activity_service import ActivityService
from account_master.services.alert_service import AlertService


def dashboard(request):
    kpis = DashboardService.get_portfolio_kpis()
    recent_activities = ActivityService.get_recent_activities(limit=20)

    if request.user.is_authenticated:
        alert_counts = AlertService.get_alert_counts(request.user)
        active_alerts = AlertService.get_active_alerts(request.user, limit=10)
    else:
        alert_counts = {
            "total": 0,
            "total_critical": 0,
            "total_warning": 0,
            "total_info": 0,
            "total_overdue": 0,
        }
        active_alerts = []

    context = {
        "kpis": kpis,
        "activities": recent_activities,
        "alert_counts": alert_counts,
        "active_alerts": active_alerts,
        "today": timezone.now().date(),
        "yesterday": (timezone.now() - timezone.timedelta(days=1)).date(),
        "breadcrumbs": [{"title": "Dashboard", "url": None}],
    }
    return render(request, "account_master/dashboard.html", context)


def portfolio_summary(request):
    kpis = DashboardService.get_portfolio_kpis()

    context = {
        "kpis": kpis,
        "portfolio_by_type": DashboardService.get_portfolio_by_loan_type(),
        "portfolio_by_status": DashboardService.get_portfolio_by_status(),
        "breadcrumbs": [
            {"title": "Dashboard", "url": "/"},
            {"title": "Portfolio Summary", "url": None},
        ],
    }
    return render(request, "account_master/portfolio_summary.html", context)
