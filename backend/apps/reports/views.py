"""Views for reports and analytics."""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.export import export_queryset_to_csv, export_queryset_to_excel

from .services import DashboardReportService


class DashboardOverviewView(APIView):
    """Return high-level KPIs for the dashboard."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        data = DashboardReportService.get_warehouse_overview(warehouse_id)
        return Response(data)


class StockMovementReportView(APIView):
    """Stock movement summary report."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        days = int(request.query_params.get("days", 30))
        data = DashboardReportService.get_stock_movement_summary(
            warehouse_id, days
        )
        return Response(data)


class TopProductsReportView(APIView):
    """Top products by stock quantity."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        limit = int(request.query_params.get("limit", 10))
        data = DashboardReportService.get_top_products(warehouse_id, limit)
        return Response(data)


class ReceivingPerformanceView(APIView):
    """Receiving performance metrics."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        days = int(request.query_params.get("days", 30))
        data = DashboardReportService.get_receiving_performance(
            warehouse_id, days
        )
        return Response(data)


class PickingPerformanceView(APIView):
    """Picking throughput and accuracy report."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        warehouse_id = request.query_params.get("warehouse_id")
        days = int(request.query_params.get("days", 30))
        data = DashboardReportService.get_picking_performance(
            warehouse_id, days
        )
        return Response(data)


class InventoryExportView(APIView):
    """Export current inventory to CSV or Excel."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.inventory.models import StockLevel

        file_format = request.query_params.get("format", "csv")
        warehouse_id = request.query_params.get("warehouse_id")

        queryset = StockLevel.objects.select_related(
            "product", "product__sku", "warehouse", "bin"
        ).filter(quantity__gt=0)

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        fields = [
            "product.sku.code",
            "product.name",
            "warehouse.name",
            "bin.code",
            "quantity",
            "reserved_quantity",
        ]
        headers = [
            "SKU",
            "Product Name",
            "Warehouse",
            "Bin",
            "Quantity",
            "Reserved",
        ]

        if file_format == "excel":
            return export_queryset_to_excel(
                queryset, fields, headers, filename="inventory_report"
            )
        return export_queryset_to_csv(
            queryset, fields, headers, filename="inventory_report"
        )
