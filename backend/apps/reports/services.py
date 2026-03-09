"""
Report generation services for WarehouseIQ.

Centralizes data aggregation for dashboard analytics and downloadable reports.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class DashboardReportService:
    """Generates aggregated data for the main dashboard."""

    @staticmethod
    def get_warehouse_overview(warehouse_id=None):
        """High-level KPIs for one or all warehouses."""
        from apps.inventory.models import Product, StockAlert, StockLevel
        from apps.picking.models import PickList
        from apps.receiving.models import ReceivingOrder
        from apps.shipping.models import Shipment
        from apps.warehouses.models import Warehouse

        wh_filter = Q()
        if warehouse_id:
            wh_filter = Q(warehouse_id=warehouse_id)

        total_products = Product.objects.filter(is_active=True).count()
        total_stock_value = (
            StockLevel.objects.filter(wh_filter, quantity__gt=0)
            .aggregate(
                value=Sum(F("quantity") * F("product__unit_cost"))
            )["value"]
            or Decimal("0.00")
        )
        total_units = (
            StockLevel.objects.filter(wh_filter).aggregate(
                total=Sum("quantity")
            )["total"]
            or 0
        )
        active_alerts = StockAlert.objects.filter(
            wh_filter, is_acknowledged=False
        ).count()
        pending_receiving = ReceivingOrder.objects.filter(
            wh_filter,
            status__in=["draft", "expected", "in_progress"],
        ).count()
        active_picks = PickList.objects.filter(
            wh_filter,
            status__in=["pending", "assigned", "in_progress"],
        ).count()
        pending_shipments = Shipment.objects.filter(
            wh_filter,
            status__in=["pending", "label_created"],
        ).count()
        warehouse_count = Warehouse.objects.filter(status="active").count()

        return {
            "total_products": total_products,
            "total_stock_units": total_units,
            "total_stock_value": float(total_stock_value),
            "active_alerts": active_alerts,
            "pending_receiving_orders": pending_receiving,
            "active_pick_lists": active_picks,
            "pending_shipments": pending_shipments,
            "active_warehouses": warehouse_count,
        }

    @staticmethod
    def get_stock_movement_summary(warehouse_id=None, days=30):
        """Summarize stock movements over the last N days."""
        from apps.inventory.models import StockMovement

        since = timezone.now() - timedelta(days=days)
        base_qs = StockMovement.objects.filter(created_at__gte=since)
        if warehouse_id:
            base_qs = base_qs.filter(warehouse_id=warehouse_id)

        summary = (
            base_qs.values("movement_type")
            .annotate(
                count=Count("id"),
                total_quantity=Sum("quantity"),
            )
            .order_by("movement_type")
        )

        return {
            "period_days": days,
            "movements": list(summary),
            "total_movements": base_qs.count(),
        }

    @staticmethod
    def get_top_products(warehouse_id=None, limit=10):
        """Top products by total stock quantity."""
        from apps.inventory.models import StockLevel

        base_qs = StockLevel.objects.filter(quantity__gt=0)
        if warehouse_id:
            base_qs = base_qs.filter(warehouse_id=warehouse_id)

        top = (
            base_qs.values(
                "product__id",
                "product__name",
                "product__sku__code",
            )
            .annotate(
                total_quantity=Sum("quantity"),
                total_reserved=Sum("reserved_quantity"),
            )
            .order_by("-total_quantity")[:limit]
        )

        return list(top)

    @staticmethod
    def get_receiving_performance(warehouse_id=None, days=30):
        """Receiving performance metrics over the last N days."""
        from apps.receiving.models import ReceivingOrder

        since = timezone.now() - timedelta(days=days)
        base_qs = ReceivingOrder.objects.filter(created_at__gte=since)
        if warehouse_id:
            base_qs = base_qs.filter(warehouse_id=warehouse_id)

        stats = base_qs.aggregate(
            total_orders=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
            avg_completion=Avg(
                "completion_percentage",
                filter=Q(status="completed"),
                default=0,
            ),
        )

        return {
            "period_days": days,
            **stats,
        }

    @staticmethod
    def get_picking_performance(warehouse_id=None, days=30):
        """Picking throughput and accuracy metrics."""
        from apps.picking.models import PickItem, PickList

        since = timezone.now() - timedelta(days=days)
        base_qs = PickList.objects.filter(created_at__gte=since)
        if warehouse_id:
            base_qs = base_qs.filter(warehouse_id=warehouse_id)

        completed = base_qs.filter(status="completed")
        total_pick_lists = base_qs.count()
        completed_count = completed.count()

        items = PickItem.objects.filter(pick_list__in=base_qs)
        total_items = items.count()
        fully_picked = items.filter(status="picked").count()
        short_picked = items.filter(status="short").count()

        accuracy = 0
        if total_items > 0:
            accuracy = round((fully_picked / total_items) * 100, 1)

        return {
            "period_days": days,
            "total_pick_lists": total_pick_lists,
            "completed_pick_lists": completed_count,
            "total_items": total_items,
            "fully_picked_items": fully_picked,
            "short_picked_items": short_picked,
            "pick_accuracy_percent": accuracy,
        }
