"""URL configuration for inventory app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BarcodeScanView,
    BatchViewSet,
    ProductViewSet,
    SKUViewSet,
    StockAlertViewSet,
    StockLevelViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register(r"skus", SKUViewSet, basename="sku")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"batches", BatchViewSet, basename="batch")
router.register(r"stock-levels", StockLevelViewSet, basename="stock-level")
router.register(r"movements", StockMovementViewSet, basename="stock-movement")
router.register(r"alerts", StockAlertViewSet, basename="stock-alert")

urlpatterns = [
    path("scan/", BarcodeScanView.as_view(), name="barcode-scan"),
    path("", include(router.urls)),
]
