"""Serializers for receiving app."""

from rest_framework import serializers

from .models import ReceivingItem, ReceivingOrder


class ReceivingItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku.code", read_only=True)
    is_fully_received = serializers.ReadOnlyField()
    variance = serializers.ReadOnlyField()
    target_bin_code = serializers.CharField(
        source="target_bin.code", read_only=True, default=None
    )

    class Meta:
        model = ReceivingItem
        fields = [
            "id",
            "receiving_order",
            "product",
            "product_name",
            "product_sku",
            "expected_quantity",
            "received_quantity",
            "rejected_quantity",
            "target_bin",
            "target_bin_code",
            "batch",
            "condition",
            "inspection_notes",
            "is_received",
            "is_fully_received",
            "variance",
            "received_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReceivingOrderSerializer(serializers.ModelSerializer):
    items = ReceivingItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    received_by_name = serializers.CharField(
        source="received_by.full_name", read_only=True, default=None
    )
    total_expected_items = serializers.ReadOnlyField()
    total_received_items = serializers.ReadOnlyField()
    completion_percentage = serializers.ReadOnlyField()

    class Meta:
        model = ReceivingOrder
        fields = [
            "id",
            "order_number",
            "warehouse",
            "warehouse_name",
            "supplier_name",
            "supplier_reference",
            "purchase_order_number",
            "status",
            "expected_date",
            "received_date",
            "received_by",
            "received_by_name",
            "notes",
            "created_by",
            "created_by_name",
            "items",
            "total_expected_items",
            "total_received_items",
            "completion_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]


class ReceivingOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating receiving orders with inline items."""

    items = ReceivingItemSerializer(many=True, required=False)

    class Meta:
        model = ReceivingOrder
        fields = [
            "id",
            "order_number",
            "warehouse",
            "supplier_name",
            "supplier_reference",
            "purchase_order_number",
            "status",
            "expected_date",
            "notes",
            "items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        order = ReceivingOrder.objects.create(
            created_by=self.context["request"].user,
            **validated_data,
        )
        for item_data in items_data:
            item_data.pop("receiving_order", None)
            ReceivingItem.objects.create(receiving_order=order, **item_data)
        return order


class ReceiveItemSerializer(serializers.Serializer):
    """Serializer for processing individual item receipt."""

    item_id = serializers.UUIDField()
    received_quantity = serializers.IntegerField(min_value=0)
    rejected_quantity = serializers.IntegerField(min_value=0, default=0)
    condition = serializers.ChoiceField(
        choices=ReceivingItem.ConditionChoices.choices,
        default=ReceivingItem.ConditionChoices.GOOD,
    )
    target_bin = serializers.UUIDField(required=False, allow_null=True)
    inspection_notes = serializers.CharField(required=False, allow_blank=True, default="")
