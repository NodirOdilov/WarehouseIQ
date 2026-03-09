"""Views for warehouses app."""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Bin, Location, Warehouse, Zone
from .serializers import (
    BinSerializer,
    LocationSerializer,
    WarehouseListSerializer,
    WarehouseSerializer,
    ZoneSerializer,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for warehouses.
    Supports filtering by status and searching by name/code.
    """

    queryset = Warehouse.objects.select_related("manager").prefetch_related("zones")
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "country", "state"]
    search_fields = ["name", "code", "city"]
    ordering_fields = ["name", "created_at", "code"]

    def get_serializer_class(self):
        if self.action == "list":
            return WarehouseListSerializer
        return WarehouseSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def zones(self, request, pk=None):
        """List all zones in a warehouse."""
        warehouse = self.get_object()
        zones = Zone.objects.filter(warehouse=warehouse)
        serializer = ZoneSerializer(zones, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Get warehouse statistics."""
        warehouse = self.get_object()
        zones = warehouse.zones.all()
        total_locations = Location.objects.filter(zone__warehouse=warehouse).count()
        total_bins = Bin.objects.filter(
            location__zone__warehouse=warehouse
        ).count()

        zone_stats = []
        for zone in zones:
            zone_stats.append({
                "id": str(zone.id),
                "name": zone.name,
                "code": zone.code,
                "type": zone.zone_type,
                "locations": zone.location_count,
                "occupancy_rate": zone.occupancy_rate,
            })

        return Response({
            "warehouse_id": str(warehouse.id),
            "warehouse_name": warehouse.name,
            "total_zones": zones.count(),
            "total_locations": total_locations,
            "total_bins": total_bins,
            "zones": zone_stats,
        })


class ZoneViewSet(viewsets.ModelViewSet):
    """CRUD operations for warehouse zones."""

    queryset = Zone.objects.select_related("warehouse").prefetch_related("locations")
    serializer_class = ZoneSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["warehouse", "zone_type", "is_active", "temperature_controlled"]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code", "created_at"]

    @action(detail=True, methods=["get"])
    def locations(self, request, pk=None):
        """List all locations in a zone."""
        zone = self.get_object()
        locations = Location.objects.filter(zone=zone).prefetch_related("bins")
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data)


class LocationViewSet(viewsets.ModelViewSet):
    """CRUD operations for warehouse locations."""

    queryset = Location.objects.select_related("zone", "zone__warehouse").prefetch_related("bins")
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["zone", "zone__warehouse", "is_active", "aisle"]
    search_fields = ["barcode", "aisle", "rack", "shelf"]
    ordering_fields = ["aisle", "rack", "shelf", "created_at"]

    @action(detail=False, methods=["get"])
    def by_barcode(self, request):
        """Look up a location by its barcode."""
        barcode = request.query_params.get("barcode", "")
        if not barcode:
            return Response(
                {"error": "barcode query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            location = Location.objects.select_related(
                "zone", "zone__warehouse"
            ).get(barcode=barcode)
            return Response(LocationSerializer(location).data)
        except Location.DoesNotExist:
            return Response(
                {"error": "Location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


class BinViewSet(viewsets.ModelViewSet):
    """CRUD operations for bins."""

    queryset = Bin.objects.select_related(
        "location", "location__zone", "location__zone__warehouse"
    )
    serializer_class = BinSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["location", "bin_type", "is_active"]
    search_fields = ["code", "barcode"]

    @action(detail=False, methods=["get"])
    def by_barcode(self, request):
        """Look up a bin by its barcode."""
        barcode = request.query_params.get("barcode", "")
        if not barcode:
            return Response(
                {"error": "barcode query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bin_obj = self.queryset.get(barcode=barcode)
            return Response(BinSerializer(bin_obj).data)
        except Bin.DoesNotExist:
            return Response(
                {"error": "Bin not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
