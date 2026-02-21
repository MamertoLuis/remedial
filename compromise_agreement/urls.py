from django.urls import path
from . import views
from .views import (
    CompromiseAgreementListView,
    CompromiseAgreementDetailView,
    CompromiseAgreementCreateView,
    CompromiseAgreementUpdateView,
    CompromiseInstallmentCreateView,
    CompromiseInstallmentUpdateView,
    mark_installment_paid,
)

urlpatterns = [
    path("", CompromiseAgreementListView.as_view(), name="compromise_agreement_list"),
    path(
        "<int:pk>/",
        CompromiseAgreementDetailView.as_view(),
        name="compromise_agreement_detail",
    ),
    path(
        "strategy/<int:strategy_id>/create/",
        CompromiseAgreementCreateView.as_view(),
        name="compromise_agreement_create",
    ),
    path(
        "<int:pk>/update/",
        CompromiseAgreementUpdateView.as_view(),
        name="compromise_agreement_update",
    ),
    path(
        "<int:agreement_pk>/installments/create/",
        CompromiseInstallmentCreateView.as_view(),
        name="compromise_installment_create",
    ),
    path(
        "installments/<int:pk>/update/",
        CompromiseInstallmentUpdateView.as_view(),
        name="compromise_installment_update",
    ),
    path(
        "installments/<int:pk>/paid/",
        mark_installment_paid,
        name="mark_installment_paid",
    ),
    path(
        "<int:pk>/generate-term-sheet-pdf/",
        views.generate_term_sheet_pdf,
        name="generate_term_sheet_pdf",
    ),
]
