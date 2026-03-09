"""Warehouse, Zone, Location, and Bin models."""

import uuid

from django.db import models


class Warehouse(models.Model):
    """Represents a physical warehouse facility."""

    class StatusChoices(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        MAINTENANCE = "maintenance", "Under Maintenance"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short unique code for the warehouse (e.g., WH-001).",
    )
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="US")
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    manager = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_warehouses",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )
    total_area_sqft = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Total warehouse area in square feet.",
    )
    max_capacity_units = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum number of storage units.",
    )
    operating_hours_start = models.TimeField(null=True, blank=True)
    operating_hours_end = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def zone_count(self):
        return self.zones.count()

    @property
    def total_locations(self):
        return Location.objects.filter(zone__warehouse=self).count()


class Zone(models.Model):
    """A functional zone within a warehouse (e.g., Receiving, Storage, Shipping)."""

    class ZoneType(models.TextChoices):
        RECEIVING = "receiving", "Receiving"
        STORAGE = "storage", "Storage"
        PICKING = "picking", "Picking"
        PACKING = "packing", "Packing"
        SHIPPING = "shipping", "Shipping"
        STAGING = "staging", "Staging"
        RETURNS = "returns", "Returns"
        QUARANTINE = "quarantine", "Quarantine"
        COLD_STORAGE = "cold_storage", "Cold Storage"
        HAZMAT = "hazmat", "Hazardous Materials"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="zones"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    zone_type = models.CharField(
        max_length=20,
        choices=ZoneType.choices,
        default=ZoneType.STORAGE,
    )
    description = models.TextField(blank=True)
    area_sqft = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    temperature_controlled = models.BooleanField(default=False)
    temperature_min = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Minimum temperature in Fahrenheit.",
    )
    temperature_max = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Maximum temperature in Fahrenheit.",
    )
    # Visual map coordinates for warehouse layout rendering
    map_x = models.IntegerField(default=0, help_text="X coordinate on warehouse map.")
    map_y = models.IntegerField(default=0, help_text="Y coordinate on warehouse map.")
    map_width = models.IntegerField(default=100, help_text="Width on warehouse map.")
    map_height = models.IntegerField(default=100, help_text="Height on warehouse map.")
    color = models.CharField(
        max_length=7, default="#3B82F6", help_text="Hex color for map rendering."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("warehouse", "code")
        ordering = ["warehouse", "code"]

    def __str__(self):
        return f"{self.warehouse.code}/{self.code} - {self.name}"

    @property
    def location_count(self):
        return self.locations.count()

    @property
    def occupancy_rate(self):
        total = self.locations.count()
        if total == 0:
            return 0
        occupied = self.locations.filter(bins__stock_levels__quantity__gt=0).distinct().count()
        return round((occupied / total) * 100, 1)


class Location(models.Model):
    """
    A specific location within a zone, identified by aisle-rack-shelf coordinates.
    Example: A-01-03 (Aisle A, Rack 01, Shelf 03).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="locations")
    aisle = models.CharField(max_length=10)
    rack = models.CharField(max_length=10)
    shelf = models.CharField(max_length=10)
    position = models.CharField(
        max_length=10, blank=True,
        help_text="Optional sub-position on the shelf.",
    )
    barcode = models.CharField(max_length=100, unique=True, db_index=True)
    max_weight_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    max_volume_m3 = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("zone", "aisle", "rack", "shelf", "position")
        ordering = ["zone", "aisle", "rack", "shelf"]

    def __str__(self):
        parts = [self.aisle, self.rack, self.shelf]
        if self.position:
            parts.append(self.position)
        return f"{self.zone.warehouse.code}/{self.zone.code}/{'-'.join(parts)}"

    @property
    def label(self):
        parts = [self.aisle, self.rack, self.shelf]
        if self.position:
            parts.append(self.position)
        return "-".join(parts)


class Bin(models.Model):
    """
    A bin is the smallest addressable unit within a location.
    A location may contain multiple bins for different products.
    """

    class BinType(models.TextChoices):
        STANDARD = "standard", "Standard"
        BULK = "bulk", "Bulk"
        SMALL_PARTS = "small_parts", "Small Parts"
        PALLET = "pallet", "Pallet"
        FLOOR = "floor", "Floor"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="bins"
    )
    code = models.CharField(max_length=50)
    barcode = models.CharField(max_length=100, unique=True, db_index=True)
    bin_type = models.CharField(
        max_length=20,
        choices=BinType.choices,
        default=BinType.STANDARD,
    )
    max_items = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum number of items this bin can hold.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("location", "code")
        ordering = ["location", "code"]

    def __str__(self):
        return f"{self.location}/{self.code}"
