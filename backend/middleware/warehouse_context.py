"""
Warehouse context middleware for WarehouseIQ.

Extracts the active warehouse from request headers and makes it
available on the request object for views and services to use.
"""

import logging

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class WarehouseContextMiddleware(MiddlewareMixin):
    """
    Reads the X-Warehouse-ID header from each request and attaches the
    corresponding Warehouse instance to ``request.warehouse``.

    Views can then reference ``request.warehouse`` instead of parsing
    the header themselves.  If the header is missing or the warehouse
    does not exist, ``request.warehouse`` is set to None.
    """

    HEADER_NAME = "HTTP_X_WAREHOUSE_ID"

    def process_request(self, request):
        request.warehouse = None
        warehouse_id = request.META.get(self.HEADER_NAME)

        if not warehouse_id:
            return

        if not request.user or not request.user.is_authenticated:
            return

        try:
            from apps.warehouses.models import Warehouse

            warehouse = Warehouse.objects.get(id=warehouse_id, status="active")
            request.warehouse = warehouse
            logger.debug(
                "Warehouse context set: %s (%s) for user %s",
                warehouse.name,
                warehouse.id,
                request.user.email,
            )
        except Warehouse.DoesNotExist:
            logger.warning(
                "Warehouse %s not found or inactive (user: %s)",
                warehouse_id,
                getattr(request.user, "email", "unknown"),
            )
        except Exception as exc:
            logger.error(
                "Error resolving warehouse context: %s", str(exc)
            )
