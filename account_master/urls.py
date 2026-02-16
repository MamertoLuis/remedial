from django.urls import path
from . import views

urlpatterns = [
    path('', views.account_list, name='account_list'),
    path('create/', views.create_account, name='create_account'),
]
