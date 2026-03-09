"""URL configuration for warehouses app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BinViewSet, LocationViewSet, WarehouseViewSet, ZoneViewSet

router = DefaultRouter()
router.register(r"", WarehouseViewSet, basename="warehouse")
router.register(r"zones", ZoneViewSet, basename="zone")
router.register(r"locations", LocationViewSet, basename="location")
router.register(r"bins", BinViewSet, basename="bin")

urlpatterns = [
    path("", include(router.urls)),
]
