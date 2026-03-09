"""
Celery tasks for inventory management.

Handles periodic stock level checks, expiry monitoring, and WebSocket alerts.
"""

import logging
from datetime import timedelta

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_low_stock_alerts(self):
    """
    Periodically check all products for low stock / out of stock conditions.
    Creates StockAlerts and sends WebSocket notifications.
    """
    from apps.inventory.models import Product, StockAlert, StockLevel
    from apps.inventory.services import InventoryService
    from apps.warehouses.models import Warehouse

    warehouses = Warehouse.objects.filter(status="active")
    alerts_created = 0

    for warehouse in warehouses:
        products = Product.objects.filter(is_active=True)
        for product in products:
            total_qty = (
                StockLevel.objects.filter(
                    product=product, warehouse=warehouse
                ).aggregate(total=Sum("quantity"))["total"]
                or 0
            )

            if total_qty == 0:
                InventoryService.create_stock_alert(
                    product=product,
                    warehouse=warehouse,
                    alert_type=StockAlert.AlertType.OUT_OF_STOCK,
                    current_quantity=0,
                    threshold=product.low_stock_threshold,
                )
                alerts_created += 1
                _send_ws_alert(warehouse.id, product, "out_of_stock", 0)

            elif total_qty <= product.low_stock_threshold:
                InventoryService.create_stock_alert(
                    product=product,
                    warehouse=warehouse,
                    alert_type=StockAlert.AlertType.LOW_STOCK,
                    current_quantity=total_qty,
                    threshold=product.low_stock_threshold,
                )
                alerts_created += 1
                _send_ws_alert(
                    warehouse.id, product, "low_stock", total_qty
                )

            elif total_qty >= product.overstock_threshold:
                InventoryService.create_stock_alert(
                    product=product,
                    warehouse=warehouse,
                    alert_type=StockAlert.AlertType.OVERSTOCK,
                    current_quantity=total_qty,
                    threshold=product.overstock_threshold,
                )
                alerts_created += 1

    logger.info("Low stock check complete. %d alerts created/updated.", alerts_created)
    return f"Checked stock levels. {alerts_created} alerts."


@shared_task(bind=True, max_retries=3)
def check_expiring_batches(self):
    """
    Check for batches that are expiring within the next 30 days.
    Creates alerts for products with expiring or expired batches.
    """
    from apps.inventory.models import Batch, Product, StockAlert, StockLevel
    from apps.inventory.services import InventoryService

    now = timezone.now().date()
    expiry_window = now + timedelta(days=30)
    alerts_created = 0

    # Expired batches
    expired_batches = Batch.objects.filter(
        expiry_date__lt=now,
        status=Batch.StatusChoices.ACTIVE,
    ).select_related("product")

    for batch in expired_batches:
        batch.status = Batch.StatusChoices.EXPIRED
        batch.save(update_fields=["status", "updated_at"])

        stock_levels = StockLevel.objects.filter(
            batch=batch, quantity__gt=0
        ).select_related("warehouse")

        for sl in stock_levels:
            InventoryService.create_stock_alert(
                product=batch.product,
                warehouse=sl.warehouse,
                alert_type=StockAlert.AlertType.EXPIRED,
                current_quantity=sl.quantity,
                threshold=0,
            )
            alerts_created += 1

    # Expiring soon
    expiring_batches = Batch.objects.filter(
        expiry_date__gte=now,
        expiry_date__lte=expiry_window,
        status=Batch.StatusChoices.ACTIVE,
    ).select_related("product")

    for batch in expiring_batches:
        stock_levels = StockLevel.objects.filter(
            batch=batch, quantity__gt=0
        ).select_related("warehouse")

        for sl in stock_levels:
            InventoryService.create_stock_alert(
                product=batch.product,
                warehouse=sl.warehouse,
                alert_type=StockAlert.AlertType.EXPIRING_SOON,
                current_quantity=sl.quantity,
                threshold=0,
            )
            alerts_created += 1

    logger.info(
        "Batch expiry check complete. %d expired, %d expiring soon.",
        expired_batches.count(),
        expiring_batches.count(),
    )
    return f"Batch expiry check done. {alerts_created} alerts."


@shared_task
def generate_inventory_snapshot():
    """
    Generate a daily inventory snapshot for reporting.
    Aggregates stock levels per product per warehouse.
    """
    from apps.inventory.models import StockLevel

    snapshot_date = timezone.now().date()
    summary = (
        StockLevel.objects.values(
            "product__sku__code",
            "product__name",
            "warehouse__name",
        )
        .annotate(
            total_quantity=Sum("quantity"),
            total_reserved=Sum("reserved_quantity"),
        )
        .order_by("warehouse__name", "product__name")
    )

    logger.info(
        "Inventory snapshot generated for %s: %d product-warehouse entries.",
        snapshot_date,
        summary.count(),
    )
    return f"Snapshot for {snapshot_date}: {summary.count()} entries."


@shared_task
def send_stock_alert_notification(alert_id: str):
    """Send an email notification for a stock alert."""
    from apps.inventory.models import StockAlert

    try:
        alert = StockAlert.objects.select_related(
            "product", "warehouse"
        ).get(id=alert_id)
    except StockAlert.DoesNotExist:
        logger.warning("StockAlert %s not found for notification.", alert_id)
        return

    # In production, integrate with email/Slack/PagerDuty here
    logger.info(
        "Stock alert notification: [%s] %s - %s at %s",
        alert.severity,
        alert.get_alert_type_display(),
        alert.product.name,
        alert.warehouse.name,
    )


def _send_ws_alert(warehouse_id, product, alert_type, quantity):
    """Send a real-time WebSocket alert to connected clients."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "stock_alerts",
            {
                "type": "stock.alert",
                "data": {
                    "warehouse_id": str(warehouse_id),
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "sku": product.sku.code,
                    "alert_type": alert_type,
                    "quantity": quantity,
                    "timestamp": timezone.now().isoformat(),
                },
            },
        )
    except Exception as e:
        logger.error("Failed to send WebSocket alert: %s", str(e))
