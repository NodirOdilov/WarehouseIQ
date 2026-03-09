"""Product, StockLevel, StockMovement, Batch, and SKU models."""

import uuid

from django.conf import settings
from django.db import models


class SKU(models.Model):
    """
    Stock Keeping Unit.
    A unique identifier for a product variant including size, color, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    barcode = models.CharField(
        max_length=100, unique=True, db_index=True, blank=True, null=True,
        help_text="UPC, EAN, or internal barcode.",
    )
    qr_code = models.ImageField(upload_to="qrcodes/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "SKU"
        verbose_name_plural = "SKUs"
        ordering = ["code"]

    def __str__(self):
        return self.code


class Product(models.Model):
    """A product in the warehouse catalog."""

    class CategoryChoices(models.TextChoices):
        ELECTRONICS = "electronics", "Electronics"
        CLOTHING = "clothing", "Clothing"
        FOOD = "food", "Food & Beverage"
        HARDWARE = "hardware", "Hardware"
        CHEMICALS = "chemicals", "Chemicals"
        RAW_MATERIALS = "raw_materials", "Raw Materials"
        PACKAGING = "packaging", "Packaging"
        FURNITURE = "furniture", "Furniture"
        AUTOMOTIVE = "automotive", "Automotive"
        OTHER = "other", "Other"

    class UnitChoices(models.TextChoices):
        EACH = "each", "Each"
        BOX = "box", "Box"
        CASE = "case", "Case"
        PALLET = "pallet", "Pallet"
        KG = "kg", "Kilogram"
        LB = "lb", "Pound"
        LITER = "liter", "Liter"
        METER = "meter", "Meter"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.OneToOneField(
        SKU, on_delete=models.PROTECT, related_name="product"
    )
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        default=CategoryChoices.OTHER,
    )
    unit_of_measure = models.CharField(
        max_length=10,
        choices=UnitChoices.choices,
        default=UnitChoices.EACH,
    )
    weight_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    length_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    width_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    height_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=settings.DEFAULT_LOW_STOCK_THRESHOLD
    )
    overstock_threshold = models.PositiveIntegerField(
        default=settings.DEFAULT_OVERSTOCK_THRESHOLD
    )
    requires_temperature_control = models.BooleanField(default=False)
    is_hazardous = models.BooleanField(default=False)
    is_fragile = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.sku.code} - {self.name}"

    @property
    def volume_cm3(self):
        if self.length_cm and self.width_cm and self.height_cm:
            return self.length_cm * self.width_cm * self.height_cm
        return None

    @property
    def total_stock(self):
        """Total stock quantity across all warehouses."""
        result = self.stock_levels.aggregate(total=models.Sum("quantity"))
        return result["total"] or 0


class Batch(models.Model):
    """
    Tracks product batches/lots with manufacturing and expiry information.
    """

    class StatusChoices(models.TextChoices):
        ACTIVE = "active", "Active"
        QUARANTINED = "quarantined", "Quarantined"
        EXPIRED = "expired", "Expired"
        RECALLED = "recalled", "Recalled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="batches"
    )
    batch_number = models.CharField(max_length=100, db_index=True)
    lot_number = models.CharField(max_length=100, blank=True)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "batch_number")
        ordering = ["-created_at"]
        verbose_name_plural = "Batches"

    def __str__(self):
        return f"{self.product.sku.code} - Batch {self.batch_number}"


class StockLevel(models.Model):
    """
    Current stock quantity of a product at a specific bin location.
    This is the source of truth for inventory levels.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_levels"
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="stock_levels",
    )
    bin = models.ForeignKey(
        "warehouses.Bin",
        on_delete=models.CASCADE,
        related_name="stock_levels",
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_levels",
    )
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(
        default=0,
        help_text="Quantity reserved for pending orders.",
    )
    last_counted_at = models.DateTimeField(null=True, blank=True)
    last_counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_counts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "bin", "batch")
        ordering = ["product", "warehouse"]
        indexes = [
            models.Index(fields=["product", "warehouse"]),
            models.Index(fields=["warehouse", "quantity"]),
        ]

    def __str__(self):
        return f"{self.product.sku.code} @ {self.bin}: {self.quantity}"

    @property
    def available_quantity(self):
        """Quantity available for allocation (not reserved)."""
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self):
        return self.quantity <= self.product.low_stock_threshold

    @property
    def is_overstock(self):
        return self.quantity >= self.product.overstock_threshold


class StockMovement(models.Model):
    """
    Tracks every stock movement for full audit trail.
    Each movement represents a change in stock level.
    """

    class MovementType(models.TextChoices):
        RECEIVE = "receive", "Receive"
        PICK = "pick", "Pick"
        TRANSFER = "transfer", "Transfer"
        ADJUSTMENT = "adjustment", "Adjustment"
        RETURN = "return", "Return"
        DAMAGE = "damage", "Damage"
        WRITE_OFF = "write_off", "Write Off"
        CYCLE_COUNT = "cycle_count", "Cycle Count"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="movements"
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField(
        help_text="Positive for inbound, negative for outbound.",
    )
    from_bin = models.ForeignKey(
        "warehouses.Bin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements_from",
    )
    to_bin = models.ForeignKey(
        "warehouses.Bin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements_to",
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
    )
    reference_type = models.CharField(
        max_length=50, blank=True,
        help_text="Type of source document (receiving_order, pick_list, etc.).",
    )
    reference_id = models.UUIDField(
        null=True, blank=True,
        help_text="ID of the source document.",
    )
    reason = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "warehouse", "-created_at"]),
            models.Index(fields=["movement_type", "-created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]

    def __str__(self):
        direction = "+" if self.quantity > 0 else ""
        return (
            f"{self.get_movement_type_display()}: "
            f"{self.product.sku.code} {direction}{self.quantity}"
        )


class StockAlert(models.Model):
    """Active stock alerts for monitoring."""

    class AlertType(models.TextChoices):
        LOW_STOCK = "low_stock", "Low Stock"
        OUT_OF_STOCK = "out_of_stock", "Out of Stock"
        OVERSTOCK = "overstock", "Overstock"
        EXPIRING_SOON = "expiring_soon", "Expiring Soon"
        EXPIRED = "expired", "Expired"

    class SeverityChoices(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="alerts"
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    severity = models.CharField(
        max_length=10,
        choices=SeverityChoices.choices,
        default=SeverityChoices.WARNING,
    )
    message = models.TextField()
    current_quantity = models.IntegerField(default=0)
    threshold = models.IntegerField(default=0)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["alert_type", "is_acknowledged"]),
            models.Index(fields=["warehouse", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.get_alert_type_display()}: {self.product.name}"
