"""WarehouseIQ URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT Authentication
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # App URLs
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/warehouses/", include("apps.warehouses.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/receiving/", include("apps.receiving.urls")),
    path("api/picking/", include("apps.picking.urls")),
    path("api/shipping/", include("apps.shipping.urls")),
    path("api/reports/", include("apps.reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar  # noqa: F401
        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except ImportError:
        pass

admin.site.site_header = "WarehouseIQ Administration"
admin.site.site_title = "WarehouseIQ"
admin.site.index_title = "Warehouse Management"
