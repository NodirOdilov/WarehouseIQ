"""URL configuration for picking app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PackingSlipViewSet, PickItemViewSet, PickListViewSet

router = DefaultRouter()
router.register(r"picklists", PickListViewSet, basename="pick-list")
router.register(r"items", PickItemViewSet, basename="pick-item")
router.register(r"packing-slips", PackingSlipViewSet, basename="packing-slip")

urlpatterns = [
    path("", include(router.urls)),
]
