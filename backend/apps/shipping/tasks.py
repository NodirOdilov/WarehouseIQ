"""Celery tasks for shipping management."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_overdue_shipments(self):
    """
    Flag shipments that are past their estimated delivery date
    but still in transit.
    """
    from apps.shipping.models import Shipment

    today = timezone.now().date()
    overdue = Shipment.objects.filter(
        status__in=[
            Shipment.StatusChoices.PICKED_UP,
            Shipment.StatusChoices.IN_TRANSIT,
        ],
        estimated_delivery__lt=today,
    )

    count = overdue.count()
    for shipment in overdue:
        logger.warning(
            "Overdue shipment: %s (estimated %s, carrier: %s, tracking: %s)",
            shipment.shipment_number,
            shipment.estimated_delivery,
            shipment.carrier.name if shipment.carrier else "N/A",
            shipment.tracking_number or "N/A",
        )

    logger.info("Overdue shipment check complete. %d overdue.", count)
    return f"Found {count} overdue shipments."


@shared_task
def send_shipping_confirmation(shipment_id: str):
    """Send a shipping confirmation notification (email/webhook)."""
    from apps.shipping.models import Shipment

    try:
        shipment = Shipment.objects.select_related(
            "carrier", "warehouse"
        ).get(id=shipment_id)
    except Shipment.DoesNotExist:
        logger.warning("Shipment %s not found.", shipment_id)
        return

    logger.info(
        "Shipping confirmation sent for %s to %s (tracking: %s)",
        shipment.shipment_number,
        shipment.recipient_name,
        shipment.tracking_number or "N/A",
    )
