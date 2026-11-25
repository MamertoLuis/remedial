from users.models import User

from account_master.services.alert_service import AlertService


# URL-name → sidebar section mapping for the ui-workspace shell.
_ACCOUNT_SECTION = {
    "account_list",
    "account_detail",
    "create_account",
    "create_account_for_borrower",
    "update_account",
    "update_account_status",
    "collection_activity_list",
    "create_collection_activity",
    "update_collection_activity",
    "create_exposure",
    "update_exposure",
    "create_delinquency_status",
    "update_delinquency_status",
    "create_remedial_strategy",
    "update_remedial_strategy",
    "remedial_strategy_detail",
    "generate_ecl_provision",
    "escalation_ladder_detail",
    "issue_escalation_notice",
}
_BORROWER_SECTION = {
    "borrower_list",
    "borrower_detail",
    "create_borrower",
    "update_borrower",
    "delete_borrower",
}
_AGREEMENT_SECTION = {
    "compromise_agreement_list",
    "compromise_agreement_detail",
    "compromise_agreement_create",
    "compromise_agreement_update",
    "compromise_installment_create",
    "compromise_installment_update",
    "mark_installment_paid",
    "generate_term_sheet_pdf",
}
_ALERT_SECTION = {
    "alert_list",
    "api_refresh_alerts",
    "api_acknowledge_alert",
    "api_resolve_alert",
    "api_dismiss_alert",
    "api_get_alert_detail",
    "api_create_alert_rule",
    "api_bulk_acknowledge",
    "api_bulk_resolve",
    "api_bulk_dismiss",
}
_REPORTING_SECTION = {
    "reports_index",
    "loan_portfolio_breakdown",
    "past_due_aging_summary",
    "npl_portfolio_analysis",
    "top_20_npl_accounts",
    "loan_officer_performance_summary",
}


def _active_section(request):
    """Return the sidebar section active for the current URL name."""
    resolver = getattr(request, "resolver_match", None)
    if resolver is None:
        return None
    url_name = resolver.url_name
    if resolver.namespace == "reporting" or url_name in _REPORTING_SECTION:
        return "reports"
    if url_name in _ACCOUNT_SECTION:
        return "accounts"
    if url_name in _BORROWER_SECTION:
        return "borrowers"
    if url_name in _AGREEMENT_SECTION:
        return "agreements"
    if url_name in _ALERT_SECTION:
        return "alerts"
    if url_name in {"dashboard", "portfolio_summary"}:
        return "dashboard"
    return None


def core_data_edit_allowed(request):
    """Inject the ``core_data_edit_allowed`` template flag.

    Mirrors the ``system_admin_required`` decorator rule so templates can hide
    fact-plane create/edit/delete controls for non-administrators while views
    remain the real security boundary.
    """
    user = getattr(request, "user", None)
    allowed = bool(
        user is not None
        and user.is_authenticated
        and user.role == User.Role.SYSTEM_ADMINISTRATOR
    )
    return {"core_data_edit_allowed": allowed}


def ui_shell(request):
    """Inject sidebar state for the ui-workspace shell.

    - ``active_section``: sidebar section for the current URL (dashboard,
      borrowers, accounts, agreements, alerts, reports) or None.
    - ``alert_counts``: open-alert counts used by the sidebar Alerts badge.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        alert_counts = AlertService.get_alert_counts(user)
    else:
        alert_counts = {
            "total": 0,
            "total_critical": 0,
            "total_warning": 0,
            "total_info": 0,
            "total_overdue": 0,
        }
    return {"active_section": _active_section(request), "alert_counts": alert_counts}

