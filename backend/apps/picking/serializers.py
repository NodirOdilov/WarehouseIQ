"""Serializers for picking app."""

from rest_framework import serializers

from .models import PackingSlip, PickItem, PickList


class PickItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku.code", read_only=True)
    from_bin_code = serializers.CharField(
        source="from_bin.code", read_only=True, default=None
    )
    from_bin_barcode = serializers.CharField(
        source="from_bin.barcode", read_only=True, default=None
    )
    location_label = serializers.SerializerMethodField()
    is_fully_picked = serializers.ReadOnlyField()
    shortage = serializers.ReadOnlyField()
    picked_by_name = serializers.CharField(
        source="picked_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = PickItem
        fields = [
            "id",
            "pick_list",
            "product",
            "product_name",
            "product_sku",
            "from_bin",
            "from_bin_code",
            "from_bin_barcode",
            "location_label",
            "batch",
            "quantity_requested",
            "quantity_picked",
            "status",
            "pick_sequence",
            "is_fully_picked",
            "shortage",
            "picked_at",
            "picked_by",
            "picked_by_name",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_location_label(self, obj):
        if obj.from_bin and obj.from_bin.location:
            return obj.from_bin.location.label
        return None


class PickListSerializer(serializers.ModelSerializer):
    items = PickItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    total_items = serializers.ReadOnlyField()
    total_quantity = serializers.ReadOnlyField()
    picked_quantity = serializers.ReadOnlyField()
    completion_percentage = serializers.ReadOnlyField()

    class Meta:
        model = PickList
        fields = [
            "id",
            "pick_number",
            "warehouse",
            "warehouse_name",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_name",
            "order_reference",
            "customer_name",
            "notes",
            "started_at",
            "completed_at",
            "created_by",
            "created_by_name",
            "items",
            "total_items",
            "total_quantity",
            "picked_quantity",
            "completion_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]


class PickListCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating pick lists with inline items."""

    items = PickItemSerializer(many=True, required=False)

    class Meta:
        model = PickList
        fields = [
            "id",
            "pick_number",
            "warehouse",
            "priority",
            "assigned_to",
            "order_reference",
            "customer_name",
            "notes",
            "items",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        pick_list = PickList.objects.create(
            created_by=self.context["request"].user,
            **validated_data,
        )
        for idx, item_data in enumerate(items_data):
            item_data.pop("pick_list", None)
            item_data.setdefault("pick_sequence", idx + 1)
            PickItem.objects.create(pick_list=pick_list, **item_data)
        return pick_list


class PickConfirmSerializer(serializers.Serializer):
    """Serializer for confirming a pick action."""

    item_id = serializers.UUIDField()
    quantity_picked = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class PackingSlipSerializer(serializers.ModelSerializer):
    pick_number = serializers.CharField(
        source="pick_list.pick_number", read_only=True
    )
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    packed_by_name = serializers.CharField(
        source="packed_by.full_name", read_only=True, default=None
    )
    items = serializers.SerializerMethodField()

    class Meta:
        model = PackingSlip
        fields = [
            "id",
            "slip_number",
            "pick_list",
            "pick_number",
            "warehouse",
            "warehouse_name",
            "status",
            "total_weight_kg",
            "package_count",
            "packed_by",
            "packed_by_name",
            "packed_at",
            "shipping_notes",
            "special_instructions",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_items(self, obj):
        """Include picked items from the associated pick list."""
        picked_items = obj.pick_list.items.filter(
            status=PickItem.StatusChoices.PICKED
        )
        return PickItemSerializer(picked_items, many=True).data
