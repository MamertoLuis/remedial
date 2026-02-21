from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from account_master.services.alert_service import AlertService
from account_master.models import Alert, AlertRule


@login_required
def refresh_alerts(request):
    """AJAX endpoint to refresh alert data."""
    try:
        # Get updated alert counts
        alert_counts = AlertService.get_alert_counts(request.user)
        active_alerts = AlertService.get_active_alerts(request.user, limit=5)

        # Prepare response data
        response_data = {
            "total_alerts": alert_counts["total"],
            "critical_count": alert_counts["critical"],
            "warning_count": alert_counts["warning"],
            "info_count": alert_counts["info"],
            "overdue_count": alert_counts["total_overdue"],
            "alerts": [
                {
                    "id": alert.alert_id,
                    "title": alert.title,
                    "message": alert.message,
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "created_at": alert.created_at.isoformat(),
                    "is_read": alert.is_read,
                    "url": alert.get_entity_url(),
                }
                for alert in active_alerts
            ],
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse(
            {
                "error": str(e),
                "total_alerts": 0,
                "critical_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "overdue_count": 0,
                "alerts": [],
            },
            status=500,
        )


@login_required
def acknowledge_alert(request):
    """AJAX endpoint to acknowledge an alert."""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    alert_id = request.POST.get("alert_id")
    if not alert_id:
        return JsonResponse(
            {"success": False, "error": "Alert ID required"}, status=400
        )

    try:
        success = AlertService.acknowledge_alert(alert_id, request.user)
        if success:
            return JsonResponse({"success": True, "message": "Alert acknowledged"})
        else:
            return JsonResponse(
                {"success": False, "error": "Failed to acknowledge alert"}, status=400
            )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def resolve_alert(request):
    """AJAX endpoint to resolve an alert."""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    alert_id = request.POST.get("alert_id")
    resolution_notes = request.POST.get("resolution_notes", "")

    if not alert_id:
        return JsonResponse(
            {"success": False, "error": "Alert ID required"}, status=400
        )

    try:
        success = AlertService.resolve_alert(alert_id, request.user, resolution_notes)
        if success:
            return JsonResponse({"success": True, "message": "Alert resolved"})
        else:
            return JsonResponse(
                {"success": False, "error": "Failed to resolve alert"}, status=400
            )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def dismiss_alert(request):
    """AJAX endpoint to dismiss an alert."""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    alert_id = request.POST.get("alert_id")
    reason = request.POST.get("reason", "")

    if not alert_id:
        return JsonResponse(
            {"success": False, "error": "Alert ID required"}, status=400
        )

    try:
        success = AlertService.dismiss_alert(alert_id, request.user, reason)
        if success:
            return JsonResponse({"success": True, "message": "Alert dismissed"})
        else:
            return JsonResponse(
                {"success": False, "error": "Failed to dismiss alert"}, status=400
            )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_alert_detail(request, alert_id):
    """Get detailed information about a specific alert."""
    try:
        alert = Alert.objects.get(alert_id=alert_id)

        # Check if user has permission to view this alert
        if alert.assigned_to and alert.assigned_to != request.user:
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        # Prepare response data with color coding
        type_colors = {
            "CRITICAL": "danger",
            "WARNING": "warning",
            "INFO": "info",
            "SUCCESS": "success",
        }

        severity_colors = {"HIGH": "danger", "MEDIUM": "warning", "LOW": "secondary"}

        status_colors = {
            "NEW": "primary",
            "ACKNOWLEDGED": "info",
            "RESOLVED": "success",
            "DISMISSED": "secondary",
        }

        response_data = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "message": alert.message,
            "type": alert.get_alert_type_display(),
            "type_color": type_colors.get(alert.alert_type, "secondary"),
            "severity": alert.get_severity_display(),
            "severity_color": severity_colors.get(alert.severity, "secondary"),
            "status": alert.get_status_display(),
            "status_color": status_colors.get(alert.status, "secondary"),
            "entity_type": alert.get_entity_type_display()
            if alert.entity_type
            else None,
            "entity_id": alert.entity_id,
            "entity_url": alert.get_entity_url(),
            "assigned_to": alert.assigned_to.get_full_name()
            if alert.assigned_to
            else None,
            "created_by": alert.created_by.get_full_name()
            if alert.created_by
            else None,
            "created_at": alert.created_at.strftime("%b %d, %Y %H:%M"),
            "due_date": alert.due_date.strftime("%b %d, %Y")
            if alert.due_date
            else None,
            "is_overdue": alert.is_overdue(),
        }

        return JsonResponse({"success": True, "alert": response_data})

    except Alert.DoesNotExist:
        return JsonResponse({"success": False, "error": "Alert not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_alert_rule(request):
    """Create a new alert rule."""
    try:
        # Extract form data
        name = request.POST.get("name")
        rule_type = request.POST.get("rule_type")
        alert_type = request.POST.get("alert_type")
        severity = request.POST.get("severity")
        description = request.POST.get("description", "")
        condition_value = request.POST.get("condition_value")
        comparison_operator = request.POST.get("comparison_operator")
        is_active = request.POST.get("is_active", "off") == "on"

        # Validate required fields
        if not all(
            [
                name,
                rule_type,
                alert_type,
                severity,
                condition_value,
                comparison_operator,
            ]
        ):
            return JsonResponse(
                {"success": False, "error": "All required fields must be provided"},
                status=400,
            )

        # Create the alert rule
        rule = AlertRule.objects.create(
            name=name,
            rule_type=rule_type,
            alert_type=alert_type,
            severity=severity,
            description=description,
            condition_value=float(condition_value),
            comparison_operator=comparison_operator,
            is_active=is_active,
            created_by=request.user,
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"Alert rule '{rule.name}' created successfully",
                "rule_id": rule.rule_id,
            }
        )

    except ValueError as e:
        return JsonResponse(
            {"success": False, "error": f"Invalid value: {str(e)}"}, status=400
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def bulk_alert_action(request):
    """Perform bulk actions on multiple alerts."""
    try:
        action = request.path.split("/")[-2]  # Extract action from URL
        alert_ids = request.POST.getlist("alert_ids[]")
        reason = request.POST.get("reason", "")

        if not alert_ids:
            return JsonResponse(
                {"success": False, "error": "No alerts selected"}, status=400
            )

        success_count = 0
        errors = []

        for alert_id in alert_ids:
            try:
                if action == "acknowledge":
                    success = AlertService.acknowledge_alert(alert_id, request.user)
                elif action == "resolve":
                    success = AlertService.resolve_alert(alert_id, request.user, reason)
                elif action == "dismiss":
                    success = AlertService.dismiss_alert(alert_id, request.user, reason)
                else:
                    errors.append(f"Invalid action: {action}")
                    continue

                if success:
                    success_count += 1
                else:
                    errors.append(f"Failed to process alert {alert_id}")

            except Exception as e:
                errors.append(f"Error processing alert {alert_id}: {str(e)}")

        if success_count > 0:
            message = f"Successfully processed {success_count} alert(s)"
            if errors:
                message += f". {len(errors)} error(s) occurred."

            return JsonResponse(
                {
                    "success": True,
                    "message": message,
                    "success_count": success_count,
                    "error_count": len(errors),
                    "errors": errors[:5],  # Return first 5 errors
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "No alerts were processed",
                    "errors": errors,
                },
                status=400,
            )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
