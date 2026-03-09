"""URL configuration for receiving app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReceivingItemViewSet, ReceivingOrderViewSet

router = DefaultRouter()
router.register(r"orders", ReceivingOrderViewSet, basename="receiving-order")
router.register(r"items", ReceivingItemViewSet, basename="receiving-item")

urlpatterns = [
    path("", include(router.urls)),
]
