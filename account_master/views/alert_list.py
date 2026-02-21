from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from account_master.services.alert_service import AlertService
from account_master.models import Alert


@login_required
def alert_list(request):
    """
    View for displaying and managing alerts with filtering and pagination.

    Args:
        request: HttpRequest object

    Returns:
        HttpResponse: Rendered alert list template
    """
    # Get base queryset
    alerts_queryset = (
        Alert.objects.all()
        .select_related("created_by", "assigned_to")
        .order_by("-created_at")
    )

    # Apply filters
    filters = Q()

    # Alert type filter
    alert_type = request.GET.get("alert_type")
    if alert_type:
        filters &= Q(alert_type=alert_type)

    # Severity filter
    severity = request.GET.get("severity")
    if severity:
        filters &= Q(severity=severity)

    # Status filter
    status = request.GET.get("status")
    if status:
        filters &= Q(status=status)

    # Entity type filter
    entity_type = request.GET.get("entity_type")
    if entity_type:
        filters &= Q(entity_type=entity_type)

    # Apply filters to queryset
    alerts_queryset = alerts_queryset.filter(filters)

    # Paginate results
    paginator = Paginator(alerts_queryset, 20)  # 20 alerts per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get alert counts
    alert_counts = AlertService.get_alert_counts(request.user)

    context = {
        "alerts": page_obj,
        "page_obj": page_obj,
        "alert_counts": alert_counts,
    }

    return render(request, "account_master/alert_list.html", context)
