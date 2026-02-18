from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BorrowerViewSet,
    LoanAccountViewSet,
    CollectionActivityLogViewSet,
    RemedialStrategyViewSet,
)

router = DefaultRouter()
router.register(r"borrowers", BorrowerViewSet)
router.register(r"accounts", LoanAccountViewSet)
router.register(r"activities", CollectionActivityLogViewSet)
router.register(r"strategies", RemedialStrategyViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
