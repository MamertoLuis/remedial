from django.urls import path
from account_master import views
from account_master.views import alerts_api
from account_master.views import alert_list

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/", views.account_list, name="account_list"),
    path("create/", views.create_account, name="create_account"),
    path(
        "borrower/<str:borrower_id>/account/create/",
        views.create_account,
        name="create_account_for_borrower",
    ),
    path("account/<str:loan_id>/", views.account_detail, name="account_detail"),
    path("account/<str:loan_id>/update/", views.update_account, name="update_account"),
    path(
        "account/<str:loan_id>/update-status/",
        views.update_account_status,
        name="update_account_status",
    ),
    path("borrowers/", views.borrower_list, name="borrower_list"),
    path("borrowers/create/", views.create_borrower, name="create_borrower"),
    path("borrower/<str:borrower_id>/", views.borrower_detail, name="borrower_detail"),
    path(
        "borrower/<str:borrower_id>/update/",
        views.update_borrower,
        name="update_borrower",
    ),
    path(
        "borrower/<str:borrower_id>/delete/",
        views.delete_borrower,
        name="delete_borrower",
    ),
    path(
        "account/<str:loan_id>/collection/",
        views.collection_activity_list,
        name="collection_activity_list",
    ),
    path(
        "account/<str:loan_id>/collection/create/",
        views.create_collection_activity,
        name="create_collection_activity",
    ),
    path(
        "account/<str:loan_id>/collection/<int:activity_id>/update/",
        views.update_collection_activity,
        name="update_collection_activity",
    ),
    path(
        "account/<str:loan_id>/exposure/create/",
        views.create_exposure,
        name="create_exposure",
    ),
    path(
        "account/<str:loan_id>/exposure/<int:exposure_id>/update/",
        views.update_exposure,
        name="update_exposure",
    ),
    path(
        "account/<str:loan_id>/delinquency/create/",
        views.create_delinquency_status,
        name="create_delinquency_status",
    ),
    path(
        "account/<str:loan_id>/delinquency/<int:delinquency_id>/update/",
        views.update_delinquency_status,
        name="update_delinquency_status",
    ),
    path(
        "account/<str:loan_id>/strategy/create/",
        views.create_remedial_strategy,
        name="create_remedial_strategy",
    ),
    path(
        "account/<str:loan_id>/strategy/<int:strategy_id>/update/",
        views.update_remedial_strategy,
        name="update_remedial_strategy",
    ),
    path(
        "account/<str:loan_id>/strategy/<int:strategy_id>/",
        views.remedial_strategy_detail,
        name="remedial_strategy_detail",
    ),
    path("search/", views.search, name="search"),
    # Alert management URLs
    path("alerts/", alert_list.alert_list, name="alert_list"),
    # Alert API URLs
    path("api/alerts/refresh/", alerts_api.refresh_alerts, name="api_refresh_alerts"),
    path(
        "api/alerts/acknowledge/",
        alerts_api.acknowledge_alert,
        name="api_acknowledge_alert",
    ),
    path("api/alerts/resolve/", alerts_api.resolve_alert, name="api_resolve_alert"),
    path("api/alerts/dismiss/", alerts_api.dismiss_alert, name="api_dismiss_alert"),
    path(
        "api/alerts/detail/<int:alert_id>/",
        alerts_api.get_alert_detail,
        name="api_get_alert_detail",
    ),
    path(
        "api/alerts/rules/create/",
        alerts_api.create_alert_rule,
        name="api_create_alert_rule",
    ),
    path(
        "api/alerts/acknowledge/",
        alerts_api.bulk_alert_action,
        name="api_bulk_acknowledge",
    ),
    path(
        "api/alerts/resolve/",
        alerts_api.bulk_alert_action,
        name="api_bulk_resolve",
    ),
    path(
        "api/alerts/dismiss/",
        alerts_api.bulk_alert_action,
        name="api_bulk_dismiss",
    ),
    path(
        "account/<str:loan_id>/ecl-provision/generate/",
        views.generate_ecl_provision,
        name="generate_ecl_provision",
    ),
]
