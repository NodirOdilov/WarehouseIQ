"""Shipment and ShipmentItem models for outbound logistics."""

import uuid

from django.conf import settings
from django.db import models


class Carrier(models.Model):
    """Shipping carrier / logistics provider."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    tracking_url_template = models.URLField(
        blank=True,
        help_text="URL template with {tracking_number} placeholder.",
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_tracking_url(self, tracking_number: str) -> str:
        if self.tracking_url_template and tracking_number:
            return self.tracking_url_template.replace(
                "{tracking_number}", tracking_number
            )
        return ""


class Shipment(models.Model):
    """An outbound shipment linked to a completed pick list / packing slip."""

    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        LABEL_CREATED = "label_created", "Label Created"
        PICKED_UP = "picked_up", "Picked Up"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        RETURNED = "returned", "Returned"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment_number = models.CharField(max_length=50, unique=True, db_index=True)
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="shipments",
    )
    packing_slip = models.OneToOneField(
        "picking.PackingSlip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipment",
    )
    carrier = models.ForeignKey(
        Carrier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipments",
    )
    tracking_number = models.CharField(max_length=200, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    # Destination address
    recipient_name = models.CharField(max_length=200)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="US")
    # Weight / dimensions
    total_weight_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    package_count = models.PositiveIntegerField(default=1)
    shipping_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Timestamps
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_shipments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["tracking_number"]),
        ]

    def __str__(self):
        return f"SH-{self.shipment_number} ({self.status})"

    @property
    def tracking_url(self):
        if self.carrier and self.tracking_number:
            return self.carrier.get_tracking_url(self.tracking_number)
        return ""
