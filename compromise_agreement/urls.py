from django.urls import path
from .views import (
    CompromiseAgreementListView,
    CompromiseAgreementDetailView,
    CompromiseAgreementCreateView,
    CompromiseAgreementUpdateView,
    CompromiseInstallmentCreateView,
    CompromiseInstallmentUpdateView,
)

urlpatterns = [
    path('', CompromiseAgreementListView.as_view(), name='compromise_agreement_list'),
    path('<int:pk>/', CompromiseAgreementDetailView.as_view(), name='compromise_agreement_detail'),
    path('create/', CompromiseAgreementCreateView.as_view(), name='compromise_agreement_create'),
    path('<int:pk>/update/', CompromiseAgreementUpdateView.as_view(), name='compromise_agreement_update'),
    path('<int:agreement_pk>/installments/create/', CompromiseInstallmentCreateView.as_view(), name='compromise_installment_create'),
    path('installments/<int:pk>/update/', CompromiseInstallmentUpdateView.as_view(), name='compromise_installment_update'),
]
