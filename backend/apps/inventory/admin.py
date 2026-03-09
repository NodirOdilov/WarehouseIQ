"""Admin configuration for inventory app."""

from django.contrib import admin

from .models import Batch, Product, SKU, StockAlert, StockLevel, StockMovement


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ["code", "barcode", "created_at"]
    search_fields = ["code", "barcode"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sku",
        "category",
        "unit_of_measure",
        "unit_cost",
        "unit_price",
        "is_active",
        "total_stock",
    ]
    list_filter = [
        "category",
        "is_active",
        "requires_temperature_control",
        "is_hazardous",
        "is_fragile",
    ]
    search_fields = ["name", "sku__code", "description"]
    raw_id_fields = ["sku"]

    def total_stock(self, obj):
        return obj.total_stock

    total_stock.short_description = "Total Stock"


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = [
        "batch_number",
        "product",
        "lot_number",
        "manufacture_date",
        "expiry_date",
        "status",
    ]
    list_filter = ["status", "expiry_date"]
    search_fields = ["batch_number", "lot_number", "product__name"]
    raw_id_fields = ["product"]


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "warehouse",
        "bin",
        "batch",
        "quantity",
        "reserved_quantity",
        "available_quantity",
    ]
    list_filter = ["warehouse"]
    search_fields = ["product__name", "product__sku__code", "bin__barcode"]
    raw_id_fields = ["product", "bin", "batch"]

    def available_quantity(self, obj):
        return obj.available_quantity

    available_quantity.short_description = "Available"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "warehouse",
        "movement_type",
        "quantity",
        "from_bin",
        "to_bin",
        "performed_by",
        "created_at",
    ]
    list_filter = ["movement_type", "warehouse", "created_at"]
    search_fields = ["product__name", "product__sku__code", "reason"]
    raw_id_fields = ["product", "from_bin", "to_bin", "performed_by"]
    date_hierarchy = "created_at"


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "warehouse",
        "alert_type",
        "severity",
        "current_quantity",
        "is_acknowledged",
        "created_at",
    ]
    list_filter = ["alert_type", "severity", "is_acknowledged", "warehouse"]
    search_fields = ["product__name", "message"]
    raw_id_fields = ["product", "acknowledged_by"]
