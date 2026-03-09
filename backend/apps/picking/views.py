"""Views for picking app."""

import logging

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.inventory.services import InventoryService

from .models import PackingSlip, PickItem, PickList
from .serializers import (
    PackingSlipSerializer,
    PickConfirmSerializer,
    PickItemSerializer,
    PickListCreateSerializer,
    PickListSerializer,
)

logger = logging.getLogger(__name__)


class PickListViewSet(viewsets.ModelViewSet):
    """Manage pick lists and process picking operations."""

    queryset = PickList.objects.select_related(
        "warehouse", "assigned_to", "created_by"
    ).prefetch_related(
        "items",
        "items__product",
        "items__product__sku",
        "items__from_bin",
        "items__from_bin__location",
    )
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "status", "priority", "assigned_to"]
    search_fields = ["pick_number", "order_reference", "customer_name"]
    ordering_fields = ["created_at", "priority"]

    def get_serializer_class(self):
        if self.action == "create":
            return PickListCreateSerializer
        return PickListSerializer

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign a pick list to a staff member."""
        pick_list = self.get_object()
        user_id = request.data.get("assigned_to")
        if not user_id:
            return Response(
                {"error": "assigned_to user ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pick_list.assigned_to_id = user_id
        pick_list.status = PickList.StatusChoices.ASSIGNED
        pick_list.save(update_fields=["assigned_to", "status", "updated_at"])
        return Response(PickListSerializer(pick_list).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Start the picking process."""
        pick_list = self.get_object()
        if pick_list.status not in (
            PickList.StatusChoices.PENDING,
            PickList.StatusChoices.ASSIGNED,
        ):
            return Response(
                {"error": f"Cannot start a pick list with status: {pick_list.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pick_list.status = PickList.StatusChoices.IN_PROGRESS
        pick_list.started_at = timezone.now()
        if not pick_list.assigned_to:
            pick_list.assigned_to = request.user
        pick_list.save(
            update_fields=["status", "started_at", "assigned_to", "updated_at"]
        )
        return Response(PickListSerializer(pick_list).data)

    @action(detail=True, methods=["post"])
    def confirm_picks(self, request, pk=None):
        """
        Confirm picked items.
        Accepts a list of items with their picked quantities.
        Processes stock movements for each confirmed pick.
        """
        pick_list = self.get_object()

        if pick_list.status not in (
            PickList.StatusChoices.IN_PROGRESS,
            PickList.StatusChoices.ASSIGNED,
        ):
            return Response(
                {"error": "Pick list must be in progress to confirm picks."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        picks_data = request.data.get("picks", [])
        if not picks_data:
            return Response(
                {"error": "No picks provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        processed = []
        errors = []

        for pick_data in picks_data:
            serializer = PickConfirmSerializer(data=pick_data)
            if not serializer.is_valid():
                errors.append({"data": pick_data, "errors": serializer.errors})
                continue

            data = serializer.validated_data
            try:
                item = PickItem.objects.select_related(
                    "product", "from_bin"
                ).get(id=data["item_id"], pick_list=pick_list)
            except PickItem.DoesNotExist:
                errors.append({
                    "item_id": str(data["item_id"]),
                    "error": "Item not found in this pick list.",
                })
                continue

            qty = data["quantity_picked"]

            if item.from_bin is None:
                errors.append({
                    "item_id": str(item.id),
                    "error": "No source bin assigned to this pick item.",
                })
                continue

            # Process stock pick through inventory service
            try:
                InventoryService.pick_stock(
                    product=item.product,
                    warehouse=pick_list.warehouse,
                    from_bin=item.from_bin,
                    quantity=qty,
                    user=request.user,
                    batch=item.batch,
                    reference_type="pick_list",
                    reference_id=pick_list.id,
                    reason=f"Picked for order {pick_list.order_reference or pick_list.pick_number}",
                )
            except ValueError as e:
                errors.append({
                    "item_id": str(item.id),
                    "error": str(e),
                })
                continue

            item.quantity_picked += qty
            item.picked_at = timezone.now()
            item.picked_by = request.user
            item.notes = data.get("notes", item.notes)

            if item.is_fully_picked:
                item.status = PickItem.StatusChoices.PICKED
            elif item.quantity_picked > 0:
                item.status = PickItem.StatusChoices.SHORT
            item.save()

            processed.append(str(item.id))

        # Check if all items are picked
        all_items = pick_list.items.all()
        if all(i.status == PickItem.StatusChoices.PICKED for i in all_items):
            pick_list.status = PickList.StatusChoices.COMPLETED
            pick_list.completed_at = timezone.now()
            pick_list.save(update_fields=["status", "completed_at", "updated_at"])

        return Response({
            "processed": processed,
            "errors": errors,
            "pick_list_status": pick_list.status,
            "completion_percentage": pick_list.completion_percentage,
        })

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Manually mark a pick list as completed."""
        pick_list = self.get_object()
        pick_list.status = PickList.StatusChoices.COMPLETED
        pick_list.completed_at = timezone.now()
        pick_list.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(PickListSerializer(pick_list).data)

    @action(detail=True, methods=["post"])
    def generate_packing_slip(self, request, pk=None):
        """Generate a packing slip from a completed pick list."""
        pick_list = self.get_object()

        if hasattr(pick_list, "packing_slip"):
            return Response(
                PackingSlipSerializer(pick_list.packing_slip).data,
                status=status.HTTP_200_OK,
            )

        # Calculate total weight
        total_weight = sum(
            (item.product.weight_kg or 0) * item.quantity_picked
            for item in pick_list.items.filter(
                status=PickItem.StatusChoices.PICKED
            ).select_related("product")
        )

        slip_number = f"PS-{pick_list.pick_number}"
        packing_slip = PackingSlip.objects.create(
            slip_number=slip_number,
            pick_list=pick_list,
            warehouse=pick_list.warehouse,
            total_weight_kg=total_weight,
            packed_by=request.user,
            packed_at=timezone.now(),
            status=PackingSlip.StatusChoices.PACKED,
        )

        return Response(
            PackingSlipSerializer(packing_slip).data,
            status=status.HTTP_201_CREATED,
        )


class PickItemViewSet(viewsets.ModelViewSet):
    """CRUD for individual pick items."""

    queryset = PickItem.objects.select_related(
        "pick_list",
        "product",
        "product__sku",
        "from_bin",
        "from_bin__location",
        "picked_by",
    )
    serializer_class = PickItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["pick_list", "product", "status"]
    search_fields = ["product__name", "product__sku__code"]


class PackingSlipViewSet(viewsets.ModelViewSet):
    """Manage packing slips."""

    queryset = PackingSlip.objects.select_related(
        "pick_list", "warehouse", "packed_by"
    ).prefetch_related("pick_list__items", "pick_list__items__product")
    serializer_class = PackingSlipSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "status"]
    search_fields = ["slip_number", "pick_list__pick_number"]
