"""URL configuration for reports app."""

from django.urls import path

from .views import (
    DashboardOverviewView,
    InventoryExportView,
    PickingPerformanceView,
    ReceivingPerformanceView,
    StockMovementReportView,
    TopProductsReportView,
)

urlpatterns = [
    path("dashboard/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("movements/", StockMovementReportView.as_view(), name="movement-report"),
    path("top-products/", TopProductsReportView.as_view(), name="top-products"),
    path("receiving/", ReceivingPerformanceView.as_view(), name="receiving-performance"),
    path("picking/", PickingPerformanceView.as_view(), name="picking-performance"),
    path("export/inventory/", InventoryExportView.as_view(), name="inventory-export"),
]
