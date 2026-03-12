from django.urls import path

from . import views

app_name = "reporting"

urlpatterns = [
    path("", views.reports_index, name="reports_index"),
    path(
        "loan-portfolio-breakdown/",
        views.loan_portfolio_breakdown,
        name="loan_portfolio_breakdown",
    ),
    path(
        "past-due-aging-summary/",
        views.past_due_aging_summary,
        name="past_due_aging_summary",
    ),
    path(
        "npl-portfolio-analysis/",
        views.npl_portfolio_analysis,
        name="npl_portfolio_analysis",
    ),
    path(
        "top-20-npl-accounts/",
        views.top_20_npl_accounts,
        name="top_20_npl_accounts",
    ),
    path(
        "loan-officer-performance-summary/",
        views.loan_officer_performance_summary,
        name="loan_officer_performance_summary",
    ),
]
