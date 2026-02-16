from django.urls import path
from . import views

urlpatterns = [
    path('', views.account_list, name='account_list'),
    path('create/', views.create_account, name='create_account'),
    path('account/<str:account_id>/', views.account_detail, name='account_detail'),
    path('account/<str:account_id>/update/', views.update_account, name='update_account'),
    path('borrower/<str:borrower_id>/', views.borrower_detail, name='borrower_detail'),
]