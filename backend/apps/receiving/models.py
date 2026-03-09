"""ReceivingOrder and ReceivingItem models."""

import uuid

from django.conf import settings
from django.db import models


class ReceivingOrder(models.Model):
    """
    Represents an inbound shipment or purchase order being received at a warehouse.
    Contains one or more ReceivingItems, each representing a product line.
    """

    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Draft"
        EXPECTED = "expected", "Expected"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        PARTIALLY_RECEIVED = "partially_received", "Partially Received"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="receiving_orders",
    )
    supplier_name = models.CharField(max_length=200)
    supplier_reference = models.CharField(max_length=100, blank=True)
    purchase_order_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_orders",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_receiving_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"RO-{self.order_number} ({self.supplier_name})"

    @property
    def total_expected_items(self):
        return self.items.aggregate(total=models.Sum("expected_quantity"))["total"] or 0

    @property
    def total_received_items(self):
        return self.items.aggregate(total=models.Sum("received_quantity"))["total"] or 0

    @property
    def completion_percentage(self):
        expected = self.total_expected_items
        if expected == 0:
            return 0
        received = self.total_received_items
        return round((received / expected) * 100, 1)


class ReceivingItem(models.Model):
    """A line item within a receiving order."""

    class ConditionChoices(models.TextChoices):
        GOOD = "good", "Good"
        DAMAGED = "damaged", "Damaged"
        DEFECTIVE = "defective", "Defective"
        MISSING = "missing", "Missing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receiving_order = models.ForeignKey(
        ReceivingOrder, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.CASCADE,
        related_name="receiving_items",
    )
    expected_quantity = models.PositiveIntegerField()
    received_quantity = models.PositiveIntegerField(default=0)
    rejected_quantity = models.PositiveIntegerField(default=0)
    target_bin = models.ForeignKey(
        "warehouses.Bin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receiving_items",
        help_text="The bin where received items should be placed.",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receiving_items",
    )
    condition = models.CharField(
        max_length=20,
        choices=ConditionChoices.choices,
        default=ConditionChoices.GOOD,
    )
    inspection_notes = models.TextField(blank=True)
    is_received = models.BooleanField(default=False)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"{self.product.name}: "
            f"{self.received_quantity}/{self.expected_quantity}"
        )

    @property
    def is_fully_received(self):
        return self.received_quantity >= self.expected_quantity

    @property
    def variance(self):
        """Difference between received and expected."""
        return self.received_quantity - self.expected_quantity
