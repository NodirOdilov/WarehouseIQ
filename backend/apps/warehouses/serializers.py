"""Serializers for warehouses app."""

from rest_framework import serializers

from .models import Bin, Location, Warehouse, Zone


class BinSerializer(serializers.ModelSerializer):
    """Serializer for Bin objects."""

    class Meta:
        model = Bin
        fields = [
            "id",
            "location",
            "code",
            "barcode",
            "bin_type",
            "max_items",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location objects."""

    label = serializers.ReadOnlyField()
    bins = BinSerializer(many=True, read_only=True)
    bin_count = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            "id",
            "zone",
            "aisle",
            "rack",
            "shelf",
            "position",
            "barcode",
            "label",
            "max_weight_kg",
            "max_volume_m3",
            "is_active",
            "bins",
            "bin_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_bin_count(self, obj):
        return obj.bins.count()


class LocationCompactSerializer(serializers.ModelSerializer):
    """Compact location serializer for nested use."""

    label = serializers.ReadOnlyField()

    class Meta:
        model = Location
        fields = ["id", "label", "barcode", "aisle", "rack", "shelf"]


class ZoneSerializer(serializers.ModelSerializer):
    """Serializer for Zone objects."""

    location_count = serializers.ReadOnlyField()
    occupancy_rate = serializers.ReadOnlyField()
    locations = LocationCompactSerializer(many=True, read_only=True)

    class Meta:
        model = Zone
        fields = [
            "id",
            "warehouse",
            "name",
            "code",
            "zone_type",
            "description",
            "area_sqft",
            "temperature_controlled",
            "temperature_min",
            "temperature_max",
            "map_x",
            "map_y",
            "map_width",
            "map_height",
            "color",
            "is_active",
            "location_count",
            "occupancy_rate",
            "locations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ZoneCompactSerializer(serializers.ModelSerializer):
    """Compact zone serializer for nested use."""

    location_count = serializers.ReadOnlyField()

    class Meta:
        model = Zone
        fields = ["id", "name", "code", "zone_type", "color", "location_count"]


class WarehouseSerializer(serializers.ModelSerializer):
    """Full warehouse serializer."""

    zone_count = serializers.ReadOnlyField()
    total_locations = serializers.ReadOnlyField()
    manager_name = serializers.CharField(
        source="manager.full_name", read_only=True, default=None
    )
    zones = ZoneCompactSerializer(many=True, read_only=True)

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "code",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
            "email",
            "manager",
            "manager_name",
            "status",
            "total_area_sqft",
            "max_capacity_units",
            "operating_hours_start",
            "operating_hours_end",
            "notes",
            "zone_count",
            "total_locations",
            "zones",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WarehouseListSerializer(serializers.ModelSerializer):
    """Lightweight warehouse serializer for list views."""

    zone_count = serializers.ReadOnlyField()
    total_locations = serializers.ReadOnlyField()
    manager_name = serializers.CharField(
        source="manager.full_name", read_only=True, default=None
    )

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "code",
            "city",
            "state",
            "country",
            "status",
            "manager_name",
            "zone_count",
            "total_locations",
        ]
