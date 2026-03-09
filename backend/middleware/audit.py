"""
Audit logging middleware for WarehouseIQ.

Logs every API request with user, method, path, and response status
for compliance and debugging purposes.
"""

import json
import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("audit")


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware that logs all API requests for audit trail compliance.
    Records: timestamp, user, method, path, status code, duration.
    """

    SKIP_PATHS = ("/admin/jsi18n/", "/static/", "/media/", "/favicon.ico")

    def process_request(self, request):
        request._audit_start_time = time.monotonic()
        request._audit_request_id = str(uuid.uuid4())

    def process_response(self, request, response):
        if any(request.path.startswith(p) for p in self.SKIP_PATHS):
            return response

        duration_ms = 0
        if hasattr(request, "_audit_start_time"):
            duration_ms = round(
                (time.monotonic() - request._audit_start_time) * 1000, 2
            )

        request_id = getattr(request, "_audit_request_id", "unknown")
        user_email = "anonymous"
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_email = request.user.email
            user_id = str(request.user.id)

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "user_email": user_email,
            "user_id": user_id,
            "duration_ms": duration_ms,
            "content_type": response.get("Content-Type", ""),
            "ip_address": self._get_client_ip(request),
        }

        if response.status_code >= 400:
            logger.warning("API request failed: %s", json.dumps(log_data))
        else:
            logger.info("API request: %s", json.dumps(log_data))

        # Add request ID to response headers for tracing
        response["X-Request-ID"] = request_id
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
