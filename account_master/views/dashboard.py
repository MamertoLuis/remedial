from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth import get_user_model
from account_master.services.dashboard_service import DashboardService
from account_master.services.activity_service import ActivityService
from account_master.services.alert_service import AlertService


def dashboard(request):
    # Get portfolio KPIs from DashboardService
    kpis = DashboardService.get_portfolio_kpis()

    # Get recent activities using ActivityService
    recent_activities = ActivityService.get_recent_activities(limit=20)

    # Get alert counts from AlertService
    alert_counts = AlertService.get_alert_counts(request.user)
    active_alerts = AlertService.get_active_alerts(request.user, limit=10)

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
