"""PickList, PickItem, and PackingSlip models."""

import uuid

from django.conf import settings
from django.db import models


class PickList(models.Model):
    """
    A pick list represents a batch of items to be picked from warehouse locations.
    Can be associated with one or more customer orders.
    """

    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        ON_HOLD = "on_hold", "On Hold"

    class PriorityChoices(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pick_number = models.CharField(max_length=50, unique=True, db_index=True)
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="pick_lists",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    priority = models.CharField(
        max_length=10,
        choices=PriorityChoices.choices,
        default=PriorityChoices.NORMAL,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_pick_lists",
    )
    order_reference = models.CharField(
        max_length=100, blank=True,
        help_text="External order reference (e.g., sales order number).",
    )
    customer_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_pick_lists",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PL-{self.pick_number} ({self.status})"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return self.items.aggregate(total=models.Sum("quantity_requested"))[
            "total"
        ] or 0

    @property
    def picked_quantity(self):
        return self.items.aggregate(total=models.Sum("quantity_picked"))[
            "total"
        ] or 0

    @property
    def completion_percentage(self):
        total = self.total_quantity
        if total == 0:
            return 0
        return round((self.picked_quantity / total) * 100, 1)


class PickItem(models.Model):
    """An individual item within a pick list."""

    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        PICKED = "picked", "Picked"
        SHORT = "short", "Short Picked"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pick_list = models.ForeignKey(
        PickList, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.CASCADE,
        related_name="pick_items",
    )
    from_bin = models.ForeignKey(
        "warehouses.Bin",
        on_delete=models.SET_NULL,
        null=True,
        related_name="pick_items",
        help_text="The bin to pick from.",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pick_items",
    )
    quantity_requested = models.PositiveIntegerField()
    quantity_picked = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    pick_sequence = models.PositiveIntegerField(
        default=0,
        help_text="Order in which items should be picked for optimal path.",
    )
    picked_at = models.DateTimeField(null=True, blank=True)
    picked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="picked_items",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pick_sequence", "created_at"]

    def __str__(self):
        return (
            f"{self.product.name}: "
            f"{self.quantity_picked}/{self.quantity_requested}"
        )

    @property
    def is_fully_picked(self):
        return self.quantity_picked >= self.quantity_requested

    @property
    def shortage(self):
        return max(0, self.quantity_requested - self.quantity_picked)


class PackingSlip(models.Model):
    """
    Packing slip generated after picking is complete.
    Lists all items packed for a shipment.
    """

    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Draft"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slip_number = models.CharField(max_length=50, unique=True, db_index=True)
    pick_list = models.OneToOneField(
        PickList,
        on_delete=models.CASCADE,
        related_name="packing_slip",
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="packing_slips",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    total_weight_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    package_count = models.PositiveIntegerField(default=1)
    packed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="packed_slips",
    )
    packed_at = models.DateTimeField(null=True, blank=True)
    shipping_notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PS-{self.slip_number}"
