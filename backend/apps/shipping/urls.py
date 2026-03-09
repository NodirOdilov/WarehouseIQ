"""URL configuration for shipping app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CarrierViewSet, ShipmentViewSet

router = DefaultRouter()
router.register(r"carriers", CarrierViewSet, basename="carrier")
router.register(r"shipments", ShipmentViewSet, basename="shipment")

urlpatterns = [
    path("", include(router.urls)),
]
