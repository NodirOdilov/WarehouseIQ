"""
Business logic services for inventory management.

Centralizes stock operations to ensure consistency and audit trail.
"""

import logging
from typing import Optional

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.warehouses.models import Bin

from .models import Batch, Product, StockAlert, StockLevel, StockMovement

logger = logging.getLogger(__name__)


class InventoryService:
    """Core service for inventory operations."""

    @staticmethod
    @transaction.atomic
    def receive_stock(
        product: Product,
        warehouse,
        to_bin: Bin,
        quantity: int,
        user,
        batch: Optional[Batch] = None,
        reference_type: str = "",
        reference_id=None,
        reason: str = "",
    ) -> StockMovement:
        """
        Receive stock into a bin location.
        Creates or updates the StockLevel and records the movement.
        """
        if quantity <= 0:
            raise ValueError("Receive quantity must be positive.")

        stock_level, _ = StockLevel.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            bin=to_bin,
            batch=batch,
            defaults={"quantity": 0},
        )
        stock_level.quantity += quantity
        stock_level.save(update_fields=["quantity", "updated_at"])

        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=StockMovement.MovementType.RECEIVE,
            quantity=quantity,
            to_bin=to_bin,
            batch=batch,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            performed_by=user,
        )

        logger.info(
            "Stock received: %s qty %d into bin %s by %s",
            product.sku.code,
            quantity,
            to_bin,
            user.email,
        )
        return movement

    @staticmethod
    @transaction.atomic
    def pick_stock(
        product: Product,
        warehouse,
        from_bin: Bin,
        quantity: int,
        user,
        batch: Optional[Batch] = None,
        reference_type: str = "",
        reference_id=None,
        reason: str = "",
    ) -> StockMovement:
        """
        Pick stock from a bin location.
        Reduces StockLevel and records the movement.
        """
        if quantity <= 0:
            raise ValueError("Pick quantity must be positive.")

        try:
            stock_level = StockLevel.objects.select_for_update().get(
                product=product,
                warehouse=warehouse,
                bin=from_bin,
                batch=batch,
            )
        except StockLevel.DoesNotExist:
            raise ValueError(
                f"No stock found for {product.sku.code} in bin {from_bin}."
            )

        if stock_level.available_quantity < quantity:
            raise ValueError(
                f"Insufficient stock. Available: {stock_level.available_quantity}, "
                f"Requested: {quantity}."
            )

        stock_level.quantity -= quantity
        stock_level.save(update_fields=["quantity", "updated_at"])

        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=StockMovement.MovementType.PICK,
            quantity=-quantity,
            from_bin=from_bin,
            batch=batch,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            performed_by=user,
        )

        logger.info(
            "Stock picked: %s qty %d from bin %s by %s",
            product.sku.code,
            quantity,
            from_bin,
            user.email,
        )
        return movement

    @staticmethod
    @transaction.atomic
    def transfer_stock(
        product: Product,
        warehouse,
        from_bin: Bin,
        to_bin: Bin,
        quantity: int,
        user,
        batch: Optional[Batch] = None,
        reason: str = "",
    ) -> StockMovement:
        """Transfer stock between bins within the same warehouse."""
        if quantity <= 0:
            raise ValueError("Transfer quantity must be positive.")
        if from_bin == to_bin:
            raise ValueError("Source and destination bins must be different.")

        # Decrease from source
        try:
            source_level = StockLevel.objects.select_for_update().get(
                product=product,
                warehouse=warehouse,
                bin=from_bin,
                batch=batch,
            )
        except StockLevel.DoesNotExist:
            raise ValueError(
                f"No stock found for {product.sku.code} in bin {from_bin}."
            )

        if source_level.available_quantity < quantity:
            raise ValueError(
                f"Insufficient stock. Available: {source_level.available_quantity}, "
                f"Requested: {quantity}."
            )

        source_level.quantity -= quantity
        source_level.save(update_fields=["quantity", "updated_at"])

        # Increase at destination
        dest_level, _ = StockLevel.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            bin=to_bin,
            batch=batch,
            defaults={"quantity": 0},
        )
        dest_level.quantity += quantity
        dest_level.save(update_fields=["quantity", "updated_at"])

        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=StockMovement.MovementType.TRANSFER,
            quantity=quantity,
            from_bin=from_bin,
            to_bin=to_bin,
            batch=batch,
            reason=reason,
            performed_by=user,
        )

        logger.info(
            "Stock transferred: %s qty %d from %s to %s by %s",
            product.sku.code,
            quantity,
            from_bin,
            to_bin,
            user.email,
        )
        return movement

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        product: Product,
        warehouse,
        bin_obj: Bin,
        new_quantity: int,
        user,
        batch: Optional[Batch] = None,
        reason: str = "Manual adjustment",
    ) -> StockMovement:
        """
        Adjust stock level at a bin to a specific quantity.
        Used for cycle counts and corrections.
        """
        stock_level, _ = StockLevel.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            bin=bin_obj,
            batch=batch,
            defaults={"quantity": 0},
        )

        delta = new_quantity - stock_level.quantity
        if delta == 0:
            return None

        stock_level.quantity = new_quantity
        stock_level.last_counted_at = timezone.now()
        stock_level.last_counted_by = user
        stock_level.save(
            update_fields=[
                "quantity",
                "last_counted_at",
                "last_counted_by",
                "updated_at",
            ]
        )

        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            movement_type=StockMovement.MovementType.ADJUSTMENT,
            quantity=delta,
            from_bin=bin_obj if delta < 0 else None,
            to_bin=bin_obj if delta > 0 else None,
            batch=batch,
            reason=reason,
            performed_by=user,
        )

        logger.info(
            "Stock adjusted: %s at bin %s, delta %+d (now %d) by %s",
            product.sku.code,
            bin_obj,
            delta,
            new_quantity,
            user.email,
        )
        return movement

    @staticmethod
    def reserve_stock(
        product: Product,
        warehouse,
        bin_obj: Bin,
        quantity: int,
        batch: Optional[Batch] = None,
    ) -> bool:
        """Reserve stock for a pending order. Returns True if successful."""
        try:
            stock_level = StockLevel.objects.select_for_update().get(
                product=product,
                warehouse=warehouse,
                bin=bin_obj,
                batch=batch,
            )
        except StockLevel.DoesNotExist:
            return False

        if stock_level.available_quantity < quantity:
            return False

        stock_level.reserved_quantity += quantity
        stock_level.save(update_fields=["reserved_quantity", "updated_at"])
        return True

    @staticmethod
    def release_reservation(
        product: Product,
        warehouse,
        bin_obj: Bin,
        quantity: int,
        batch: Optional[Batch] = None,
    ) -> bool:
        """Release a stock reservation."""
        try:
            stock_level = StockLevel.objects.get(
                product=product,
                warehouse=warehouse,
                bin=bin_obj,
                batch=batch,
            )
        except StockLevel.DoesNotExist:
            return False

        stock_level.reserved_quantity = max(
            0, stock_level.reserved_quantity - quantity
        )
        stock_level.save(update_fields=["reserved_quantity", "updated_at"])
        return True

    @staticmethod
    def get_product_stock_summary(product: Product) -> dict:
        """Get aggregated stock summary for a product across all warehouses."""
        levels = (
            StockLevel.objects.filter(product=product)
            .values("warehouse__name", "warehouse__id")
            .annotate(
                total_quantity=Sum("quantity"),
                total_reserved=Sum("reserved_quantity"),
            )
        )
        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "sku": product.sku.code,
            "total_stock": product.total_stock,
            "by_warehouse": [
                {
                    "warehouse_id": str(level["warehouse__id"]),
                    "warehouse_name": level["warehouse__name"],
                    "quantity": level["total_quantity"],
                    "reserved": level["total_reserved"],
                    "available": level["total_quantity"] - level["total_reserved"],
                }
                for level in levels
            ],
        }

    @staticmethod
    def create_stock_alert(
        product: Product,
        warehouse,
        alert_type: str,
        current_quantity: int,
        threshold: int,
    ) -> StockAlert:
        """Create a stock alert if one doesn't already exist for this product/warehouse/type."""
        existing = StockAlert.objects.filter(
            product=product,
            warehouse=warehouse,
            alert_type=alert_type,
            is_acknowledged=False,
        ).first()

        if existing:
            existing.current_quantity = current_quantity
            existing.save(update_fields=["current_quantity"])
            return existing

        severity_map = {
            StockAlert.AlertType.OUT_OF_STOCK: StockAlert.SeverityChoices.CRITICAL,
            StockAlert.AlertType.LOW_STOCK: StockAlert.SeverityChoices.WARNING,
            StockAlert.AlertType.OVERSTOCK: StockAlert.SeverityChoices.INFO,
            StockAlert.AlertType.EXPIRING_SOON: StockAlert.SeverityChoices.WARNING,
            StockAlert.AlertType.EXPIRED: StockAlert.SeverityChoices.CRITICAL,
        }

        message_map = {
            StockAlert.AlertType.OUT_OF_STOCK: (
                f"{product.name} is out of stock at {warehouse.name}."
            ),
            StockAlert.AlertType.LOW_STOCK: (
                f"{product.name} is below minimum threshold "
                f"({current_quantity}/{threshold}) at {warehouse.name}."
            ),
            StockAlert.AlertType.OVERSTOCK: (
                f"{product.name} exceeds maximum threshold "
                f"({current_quantity}/{threshold}) at {warehouse.name}."
            ),
            StockAlert.AlertType.EXPIRING_SOON: (
                f"{product.name} has batches expiring soon at {warehouse.name}."
            ),
            StockAlert.AlertType.EXPIRED: (
                f"{product.name} has expired batches at {warehouse.name}."
            ),
        }

        return StockAlert.objects.create(
            product=product,
            warehouse=warehouse,
            alert_type=alert_type,
            severity=severity_map.get(alert_type, StockAlert.SeverityChoices.INFO),
            message=message_map.get(alert_type, "Stock alert"),
            current_quantity=current_quantity,
            threshold=threshold,
        )
