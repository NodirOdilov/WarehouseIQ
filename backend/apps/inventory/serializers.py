"""Serializers for inventory app."""

from rest_framework import serializers

from .models import Batch, Product, SKU, StockAlert, StockLevel, StockMovement


class SKUSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = ["id", "code", "barcode", "qr_code", "created_at"]
        read_only_fields = ["id", "qr_code", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    """Full product serializer."""

    sku_code = serializers.CharField(source="sku.code", read_only=True)
    sku_barcode = serializers.CharField(source="sku.barcode", read_only=True)
    total_stock = serializers.ReadOnlyField()
    volume_cm3 = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "sku_code",
            "sku_barcode",
            "name",
            "description",
            "category",
            "unit_of_measure",
            "weight_kg",
            "length_cm",
            "width_cm",
            "height_cm",
            "volume_cm3",
            "unit_cost",
            "unit_price",
            "low_stock_threshold",
            "overstock_threshold",
            "requires_temperature_control",
            "is_hazardous",
            "is_fragile",
            "is_active",
            "image",
            "total_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product list views."""

    sku_code = serializers.CharField(source="sku.code", read_only=True)
    total_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "sku_code",
            "name",
            "category",
            "unit_of_measure",
            "unit_cost",
            "unit_price",
            "total_stock",
            "is_active",
        ]


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating products with inline SKU creation."""

    sku_code = serializers.CharField(write_only=True)
    sku_barcode = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku_code",
            "sku_barcode",
            "name",
            "description",
            "category",
            "unit_of_measure",
            "weight_kg",
            "length_cm",
            "width_cm",
            "height_cm",
            "unit_cost",
            "unit_price",
            "low_stock_threshold",
            "overstock_threshold",
            "requires_temperature_control",
            "is_hazardous",
            "is_fragile",
            "image",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        sku_code = validated_data.pop("sku_code")
        sku_barcode = validated_data.pop("sku_barcode", None)
        sku = SKU.objects.create(code=sku_code, barcode=sku_barcode or None)
        product = Product.objects.create(sku=sku, **validated_data)
        return product


class BatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku.code", read_only=True)

    class Meta:
        model = Batch
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "batch_number",
            "lot_number",
            "manufacture_date",
            "expiry_date",
            "supplier",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockLevelSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku.code", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    bin_code = serializers.CharField(source="bin.code", read_only=True)
    bin_barcode = serializers.CharField(source="bin.barcode", read_only=True)
    available_quantity = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    batch_number = serializers.CharField(
        source="batch.batch_number", read_only=True, default=None
    )

    class Meta:
        model = StockLevel
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "warehouse",
            "warehouse_name",
            "bin",
            "bin_code",
            "bin_barcode",
            "batch",
            "batch_number",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "is_low_stock",
            "last_counted_at",
            "last_counted_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku.code", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    from_bin_code = serializers.CharField(
        source="from_bin.code", read_only=True, default=None
    )
    to_bin_code = serializers.CharField(
        source="to_bin.code", read_only=True, default=None
    )
    performed_by_name = serializers.CharField(
        source="performed_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "warehouse",
            "warehouse_name",
            "movement_type",
            "quantity",
            "from_bin",
            "from_bin_code",
            "to_bin",
            "to_bin_code",
            "batch",
            "reference_type",
            "reference_id",
            "reason",
            "performed_by",
            "performed_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "performed_by", "created_at"]


class StockMovementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating stock movements (processes inventory changes)."""

    class Meta:
        model = StockMovement
        fields = [
            "product",
            "warehouse",
            "movement_type",
            "quantity",
            "from_bin",
            "to_bin",
            "batch",
            "reference_type",
            "reference_id",
            "reason",
        ]

    def validate(self, attrs):
        movement_type = attrs.get("movement_type")
        from_bin = attrs.get("from_bin")
        to_bin = attrs.get("to_bin")

        if movement_type == StockMovement.MovementType.TRANSFER:
            if not from_bin or not to_bin:
                raise serializers.ValidationError(
                    "Transfer movements require both from_bin and to_bin."
                )
            if from_bin == to_bin:
                raise serializers.ValidationError(
                    "Source and destination bins must be different."
                )

        if movement_type == StockMovement.MovementType.RECEIVE and not to_bin:
            raise serializers.ValidationError(
                "Receive movements require a to_bin."
            )

        if movement_type in (
            StockMovement.MovementType.PICK,
            StockMovement.MovementType.DAMAGE,
            StockMovement.MovementType.WRITE_OFF,
        ) and not from_bin:
            raise serializers.ValidationError(
                f"{movement_type} movements require a from_bin."
            )

        return attrs


class StockAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku.code", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = StockAlert
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "warehouse",
            "warehouse_name",
            "alert_type",
            "severity",
            "message",
            "current_quantity",
            "threshold",
            "is_acknowledged",
            "acknowledged_by",
            "acknowledged_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "product",
            "warehouse",
            "alert_type",
            "severity",
            "message",
            "current_quantity",
            "threshold",
            "created_at",
        ]


class BarcodeScanSerializer(serializers.Serializer):
    """Serializer for barcode/QR scan input."""

    barcode = serializers.CharField(max_length=200)
    scan_type = serializers.ChoiceField(
        choices=[("product", "Product"), ("location", "Location"), ("bin", "Bin")],
        default="product",
    )
