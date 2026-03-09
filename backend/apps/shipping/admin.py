"""Admin configuration for shipping app."""

from django.contrib import admin

from .models import Carrier, Shipment


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active", "contact_email"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        "shipment_number",
        "warehouse",
        "carrier",
        "status",
        "recipient_name",
        "tracking_number",
        "shipped_at",
        "created_at",
    ]
    list_filter = ["status", "carrier", "warehouse"]
    search_fields = [
        "shipment_number",
        "tracking_number",
        "recipient_name",
    ]
    raw_id_fields = ["warehouse", "packing_slip", "carrier", "created_by"]
    readonly_fields = ["created_at", "updated_at"]
