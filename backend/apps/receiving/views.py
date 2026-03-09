"""Views for receiving app."""

import logging

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.inventory.services import InventoryService
from apps.warehouses.models import Bin

from .models import ReceivingItem, ReceivingOrder
from .serializers import (
    ReceiveItemSerializer,
    ReceivingItemSerializer,
    ReceivingOrderCreateSerializer,
    ReceivingOrderSerializer,
)

logger = logging.getLogger(__name__)


class ReceivingOrderViewSet(viewsets.ModelViewSet):
    """Manage receiving orders and process inbound shipments."""

    queryset = ReceivingOrder.objects.select_related(
        "warehouse", "created_by", "received_by"
    ).prefetch_related("items", "items__product", "items__product__sku")
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "status", "supplier_name"]
    search_fields = [
        "order_number",
        "supplier_name",
        "supplier_reference",
        "purchase_order_number",
    ]
    ordering_fields = ["created_at", "expected_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return ReceivingOrderCreateSerializer
        return ReceivingOrderSerializer

    @action(detail=True, methods=["post"])
    def receive_items(self, request, pk=None):
        """
        Process receipt of items within a receiving order.
        Accepts a list of items with received quantities.
        Updates stock levels accordingly.
        """
        order = self.get_object()

        if order.status in (
            ReceivingOrder.StatusChoices.COMPLETED,
            ReceivingOrder.StatusChoices.CANCELLED,
        ):
            return Response(
                {"error": f"Cannot receive items for a {order.status} order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_data = request.data.get("items", [])
        if not items_data:
            return Response(
                {"error": "No items provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        processed = []
        errors = []

        for item_data in items_data:
            serializer = ReceiveItemSerializer(data=item_data)
            if not serializer.is_valid():
                errors.append({
                    "item": item_data,
                    "errors": serializer.errors,
                })
                continue

            data = serializer.validated_data
            try:
                item = ReceivingItem.objects.get(
                    id=data["item_id"],
                    receiving_order=order,
                )
            except ReceivingItem.DoesNotExist:
                errors.append({
                    "item_id": str(data["item_id"]),
                    "error": "Item not found in this order.",
                })
                continue

            received_qty = data["received_quantity"]
            rejected_qty = data["rejected_quantity"]
            target_bin_id = data.get("target_bin") or (
                item.target_bin_id if item.target_bin_id else None
            )

            if not target_bin_id:
                errors.append({
                    "item_id": str(item.id),
                    "error": "No target bin specified.",
                })
                continue

            try:
                target_bin = Bin.objects.get(id=target_bin_id)
            except Bin.DoesNotExist:
                errors.append({
                    "item_id": str(item.id),
                    "error": "Target bin not found.",
                })
                continue

            # Process receipt through inventory service
            try:
                InventoryService.receive_stock(
                    product=item.product,
                    warehouse=order.warehouse,
                    to_bin=target_bin,
                    quantity=received_qty,
                    user=request.user,
                    batch=item.batch,
                    reference_type="receiving_order",
                    reference_id=order.id,
                    reason=f"Received from {order.supplier_name} "
                           f"(RO: {order.order_number})",
                )
            except ValueError as e:
                errors.append({
                    "item_id": str(item.id),
                    "error": str(e),
                })
                continue

            # Update receiving item
            item.received_quantity += received_qty
            item.rejected_quantity += rejected_qty
            item.target_bin = target_bin
            item.condition = data.get("condition", item.condition)
            item.inspection_notes = data.get("inspection_notes", item.inspection_notes)
            item.is_received = item.is_fully_received
            if item.is_received:
                item.received_at = timezone.now()
            item.save()

            processed.append(str(item.id))

        # Update order status
        all_items = order.items.all()
        if all(i.is_received for i in all_items):
            order.status = ReceivingOrder.StatusChoices.COMPLETED
            order.received_date = timezone.now()
            order.received_by = request.user
        elif any(i.received_quantity > 0 for i in all_items):
            order.status = ReceivingOrder.StatusChoices.PARTIALLY_RECEIVED
        else:
            order.status = ReceivingOrder.StatusChoices.IN_PROGRESS
        order.save()

        response_data = {
            "processed": processed,
            "errors": errors,
            "order_status": order.status,
            "completion_percentage": order.completion_percentage,
        }

        return Response(
            response_data,
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a receiving order."""
        order = self.get_object()
        if order.status == ReceivingOrder.StatusChoices.COMPLETED:
            return Response(
                {"error": "Cannot cancel a completed order."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = ReceivingOrder.StatusChoices.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        return Response(ReceivingOrderSerializer(order).data)


class ReceivingItemViewSet(viewsets.ModelViewSet):
    """CRUD for individual receiving items."""

    queryset = ReceivingItem.objects.select_related(
        "receiving_order", "product", "product__sku", "target_bin"
    )
    serializer_class = ReceivingItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["receiving_order", "product", "is_received", "condition"]
    search_fields = ["product__name", "product__sku__code"]
