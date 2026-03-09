"""Serializers for shipping app."""

from rest_framework import serializers

from .models import Carrier, Shipment


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = [
            "id",
            "name",
            "code",
            "tracking_url_template",
            "contact_email",
            "contact_phone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ShipmentSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    carrier_name = serializers.CharField(
        source="carrier.name", read_only=True, default=None
    )
    packing_slip_number = serializers.CharField(
        source="packing_slip.slip_number", read_only=True, default=None
    )
    tracking_url = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = Shipment
        fields = [
            "id",
            "shipment_number",
            "warehouse",
            "warehouse_name",
            "packing_slip",
            "packing_slip_number",
            "carrier",
            "carrier_name",
            "tracking_number",
            "tracking_url",
            "status",
            "recipient_name",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "total_weight_kg",
            "package_count",
            "shipping_cost",
            "shipped_at",
            "delivered_at",
            "estimated_delivery",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class ShipmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            "shipment_number",
            "warehouse",
            "packing_slip",
            "carrier",
            "tracking_number",
            "recipient_name",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "total_weight_kg",
            "package_count",
            "shipping_cost",
            "estimated_delivery",
            "notes",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
