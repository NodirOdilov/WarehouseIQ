"""Celery configuration for WarehouseIQ."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("warehouseiq")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    "check-low-stock-alerts": {
        "task": "apps.inventory.tasks.check_low_stock_alerts",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "alerts"},
    },
    "check-expiring-batches": {
        "task": "apps.inventory.tasks.check_expiring_batches",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "alerts"},
    },
    "generate-daily-inventory-snapshot": {
        "task": "apps.inventory.tasks.generate_inventory_snapshot",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "reports"},
    },
}

app.conf.task_routes = {
    "apps.inventory.tasks.check_low_stock_alerts": {"queue": "alerts"},
    "apps.inventory.tasks.check_expiring_batches": {"queue": "alerts"},
    "apps.inventory.tasks.generate_inventory_snapshot": {"queue": "reports"},
    "apps.shipping.tasks.*": {"queue": "shipping"},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
