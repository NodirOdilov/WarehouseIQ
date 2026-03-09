"""Views for inventory app."""

import logging

from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.warehouses.models import Bin, Location
from apps.warehouses.serializers import BinSerializer, LocationSerializer

from .models import Batch, Product, SKU, StockAlert, StockLevel, StockMovement
from .serializers import (
    BarcodeScanSerializer,
    BatchSerializer,
    ProductCreateSerializer,
    ProductListSerializer,
    ProductSerializer,
    SKUSerializer,
    StockAlertSerializer,
    StockLevelSerializer,
    StockMovementCreateSerializer,
    StockMovementSerializer,
)
from .services import InventoryService

logger = logging.getLogger(__name__)


class SKUViewSet(viewsets.ModelViewSet):
    """CRUD operations for SKUs."""

    queryset = SKU.objects.all()
    serializer_class = SKUSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["code", "barcode"]


class ProductViewSet(viewsets.ModelViewSet):
    """CRUD operations for products."""

    queryset = Product.objects.select_related("sku").all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = [
        "category",
        "is_active",
        "requires_temperature_control",
        "is_hazardous",
    ]
    search_fields = ["name", "sku__code", "sku__barcode", "description"]
    ordering_fields = ["name", "created_at", "unit_cost", "unit_price"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action == "create":
            return ProductCreateSerializer
        return ProductSerializer

    @action(detail=True, methods=["get"])
    def stock_summary(self, request, pk=None):
        """Get stock summary for a product across all warehouses."""
        product = self.get_object()
        summary = InventoryService.get_product_stock_summary(product)
        return Response(summary)

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        """Get recent stock movements for a product."""
        product = self.get_object()
        movements = StockMovement.objects.filter(product=product).select_related(
            "warehouse", "performed_by", "from_bin", "to_bin"
        )[:50]
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def batches(self, request, pk=None):
        """List all batches for a product."""
        product = self.get_object()
        batches = Batch.objects.filter(product=product)
        serializer = BatchSerializer(batches, many=True)
        return Response(serializer.data)


class BatchViewSet(viewsets.ModelViewSet):
    """CRUD operations for batches."""

    queryset = Batch.objects.select_related("product", "product__sku").all()
    serializer_class = BatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["product", "status"]
    search_fields = ["batch_number", "lot_number", "supplier"]
    ordering_fields = ["created_at", "expiry_date"]


class StockLevelViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to current stock levels."""

    queryset = StockLevel.objects.select_related(
        "product",
        "product__sku",
        "warehouse",
        "bin",
        "batch",
    ).all()
    serializer_class = StockLevelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["product", "warehouse", "bin"]
    search_fields = ["product__name", "product__sku__code", "bin__barcode"]
    ordering_fields = ["quantity", "updated_at"]

    @action(detail=False, methods=["get"])
    def by_warehouse(self, request):
        """Get aggregated stock levels by warehouse."""
        warehouse_id = request.query_params.get("warehouse_id")
        if not warehouse_id:
            return Response(
                {"error": "warehouse_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        levels = (
            self.queryset.filter(warehouse_id=warehouse_id)
            .values(
                "product__id",
                "product__name",
                "product__sku__code",
            )
            .annotate(
                total_quantity=Sum("quantity"),
                total_reserved=Sum("reserved_quantity"),
            )
            .order_by("product__name")
        )
        return Response(list(levels))

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """List all products below their low stock threshold."""
        warehouse_id = request.query_params.get("warehouse_id")
        queryset = self.queryset.filter(quantity__gt=0)
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        low_stock_items = [
            sl for sl in queryset if sl.is_low_stock
        ]
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ModelViewSet):
    """
    Manage stock movements.
    Creating a movement triggers the actual inventory change.
    """

    queryset = StockMovement.objects.select_related(
        "product",
        "product__sku",
        "warehouse",
        "performed_by",
        "from_bin",
        "to_bin",
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["product", "warehouse", "movement_type"]
    search_fields = ["product__name", "product__sku__code"]
    ordering_fields = ["created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def perform_create(self, serializer):
        """Process the stock movement through the inventory service."""
        data = serializer.validated_data
        movement_type = data["movement_type"]
        product = data["product"]
        warehouse = data["warehouse"]
        user = self.request.user
        batch = data.get("batch")
        reason = data.get("reason", "")
        ref_type = data.get("reference_type", "")
        ref_id = data.get("reference_id")

        service = InventoryService

        if movement_type == StockMovement.MovementType.RECEIVE:
            movement = service.receive_stock(
                product=product,
                warehouse=warehouse,
                to_bin=data["to_bin"],
                quantity=abs(data["quantity"]),
                user=user,
                batch=batch,
                reference_type=ref_type,
                reference_id=ref_id,
                reason=reason,
            )
        elif movement_type == StockMovement.MovementType.PICK:
            movement = service.pick_stock(
                product=product,
                warehouse=warehouse,
                from_bin=data["from_bin"],
                quantity=abs(data["quantity"]),
                user=user,
                batch=batch,
                reference_type=ref_type,
                reference_id=ref_id,
                reason=reason,
            )
        elif movement_type == StockMovement.MovementType.TRANSFER:
            movement = service.transfer_stock(
                product=product,
                warehouse=warehouse,
                from_bin=data["from_bin"],
                to_bin=data["to_bin"],
                quantity=abs(data["quantity"]),
                user=user,
                batch=batch,
                reason=reason,
            )
        elif movement_type == StockMovement.MovementType.ADJUSTMENT:
            movement = service.adjust_stock(
                product=product,
                warehouse=warehouse,
                bin_obj=data.get("to_bin") or data.get("from_bin"),
                new_quantity=abs(data["quantity"]),
                user=user,
                batch=batch,
                reason=reason,
            )
        else:
            # For other types (damage, write_off, return), use generic handling
            if data.get("from_bin"):
                service.pick_stock(
                    product=product,
                    warehouse=warehouse,
                    from_bin=data["from_bin"],
                    quantity=abs(data["quantity"]),
                    user=user,
                    batch=batch,
                    reference_type=ref_type,
                    reference_id=ref_id,
                    reason=f"[{movement_type}] {reason}",
                )
            elif data.get("to_bin"):
                service.receive_stock(
                    product=product,
                    warehouse=warehouse,
                    to_bin=data["to_bin"],
                    quantity=abs(data["quantity"]),
                    user=user,
                    batch=batch,
                    reference_type=ref_type,
                    reference_id=ref_id,
                    reason=f"[{movement_type}] {reason}",
                )


class StockAlertViewSet(viewsets.ModelViewSet):
    """Manage stock alerts."""

    queryset = StockAlert.objects.select_related(
        "product", "product__sku", "warehouse"
    ).all()
    serializer_class = StockAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "alert_type", "severity", "is_acknowledged"]
    ordering_fields = ["created_at", "severity"]

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge a stock alert."""
        alert = self.get_object()
        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save(
            update_fields=[
                "is_acknowledged",
                "acknowledged_by",
                "acknowledged_at",
            ]
        )
        return Response(StockAlertSerializer(alert).data)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """List all active (unacknowledged) alerts."""
        alerts = self.queryset.filter(is_acknowledged=False)
        warehouse_id = request.query_params.get("warehouse_id")
        if warehouse_id:
            alerts = alerts.filter(warehouse_id=warehouse_id)
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)


class BarcodeScanView(APIView):
    """
    Universal barcode/QR scan endpoint.
    Looks up products, locations, or bins by barcode.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BarcodeScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        barcode = serializer.validated_data["barcode"]
        scan_type = serializer.validated_data["scan_type"]

        if scan_type == "product":
            try:
                sku = SKU.objects.get(barcode=barcode)
                product = sku.product
                return Response({
                    "type": "product",
                    "data": ProductSerializer(product).data,
                })
            except (SKU.DoesNotExist, Product.DoesNotExist):
                pass

        elif scan_type == "location":
            try:
                location = Location.objects.select_related(
                    "zone", "zone__warehouse"
                ).get(barcode=barcode)
                return Response({
                    "type": "location",
                    "data": LocationSerializer(location).data,
                })
            except Location.DoesNotExist:
                pass

        elif scan_type == "bin":
            try:
                bin_obj = Bin.objects.select_related(
                    "location", "location__zone", "location__zone__warehouse"
                ).get(barcode=barcode)
                return Response({
                    "type": "bin",
                    "data": BinSerializer(bin_obj).data,
                })
            except Bin.DoesNotExist:
                pass

        # Auto-detect: try all types
        try:
            sku = SKU.objects.get(barcode=barcode)
            product = sku.product
            return Response({
                "type": "product",
                "data": ProductSerializer(product).data,
            })
        except (SKU.DoesNotExist, Product.DoesNotExist):
            pass

        try:
            bin_obj = Bin.objects.get(barcode=barcode)
            return Response({
                "type": "bin",
                "data": BinSerializer(bin_obj).data,
            })
        except Bin.DoesNotExist:
            pass

        try:
            location = Location.objects.get(barcode=barcode)
            return Response({
                "type": "location",
                "data": LocationSerializer(location).data,
            })
        except Location.DoesNotExist:
            pass

        return Response(
            {"error": f"No item found with barcode: {barcode}"},
            status=status.HTTP_404_NOT_FOUND,
        )
