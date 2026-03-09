"""Views for shipping app."""

import logging

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Carrier, Shipment
from .serializers import (
    CarrierSerializer,
    ShipmentCreateSerializer,
    ShipmentSerializer,
)

logger = logging.getLogger(__name__)


class CarrierViewSet(viewsets.ModelViewSet):
    """CRUD operations for shipping carriers."""

    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code"]


class ShipmentViewSet(viewsets.ModelViewSet):
    """Manage outbound shipments."""

    queryset = Shipment.objects.select_related(
        "warehouse", "carrier", "packing_slip", "created_by"
    )
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "status", "carrier"]
    search_fields = [
        "shipment_number",
        "tracking_number",
        "recipient_name",
    ]
    ordering_fields = ["created_at", "shipped_at", "status"]

    def get_serializer_class(self):
        if self.action == "create":
            return ShipmentCreateSerializer
        return ShipmentSerializer

    @action(detail=True, methods=["post"])
    def mark_shipped(self, request, pk=None):
        """Mark a shipment as shipped / picked up."""
        shipment = self.get_object()
        tracking_number = request.data.get(
            "tracking_number", shipment.tracking_number
        )
        carrier_id = request.data.get("carrier")

        if carrier_id:
            shipment.carrier_id = carrier_id
        shipment.tracking_number = tracking_number
        shipment.status = Shipment.StatusChoices.PICKED_UP
        shipment.shipped_at = timezone.now()
        shipment.save(
            update_fields=[
                "carrier",
                "tracking_number",
                "status",
                "shipped_at",
                "updated_at",
            ]
        )
        return Response(ShipmentSerializer(shipment).data)

    @action(detail=True, methods=["post"])
    def mark_delivered(self, request, pk=None):
        """Mark a shipment as delivered."""
        shipment = self.get_object()
        shipment.status = Shipment.StatusChoices.DELIVERED
        shipment.delivered_at = timezone.now()
        shipment.save(
            update_fields=["status", "delivered_at", "updated_at"]
        )
        return Response(ShipmentSerializer(shipment).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a shipment."""
        shipment = self.get_object()
        if shipment.status in (
            Shipment.StatusChoices.DELIVERED,
            Shipment.StatusChoices.CANCELLED,
        ):
            return Response(
                {"error": f"Cannot cancel a {shipment.status} shipment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shipment.status = Shipment.StatusChoices.CANCELLED
        shipment.save(update_fields=["status", "updated_at"])
        return Response(ShipmentSerializer(shipment).data)

    @action(detail=False, methods=["get"])
    def active(self, request):
        """List all active (non-delivered, non-cancelled) shipments."""
        active_statuses = [
            Shipment.StatusChoices.PENDING,
            Shipment.StatusChoices.LABEL_CREATED,
            Shipment.StatusChoices.PICKED_UP,
            Shipment.StatusChoices.IN_TRANSIT,
        ]
        shipments = self.queryset.filter(status__in=active_statuses)
        warehouse_id = request.query_params.get("warehouse_id")
        if warehouse_id:
            shipments = shipments.filter(warehouse_id=warehouse_id)
        serializer = ShipmentSerializer(shipments, many=True)
        return Response(serializer.data)
