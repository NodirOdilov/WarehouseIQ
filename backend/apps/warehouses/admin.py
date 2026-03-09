"""Admin configuration for warehouses app."""

from django.contrib import admin

from .models import Bin, Location, Warehouse, Zone


class ZoneInline(admin.TabularInline):
    model = Zone
    extra = 0
    fields = ["name", "code", "zone_type", "is_active"]
    show_change_link = True


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "city",
        "state",
        "country",
        "status",
        "manager",
        "zone_count",
    ]
    list_filter = ["status", "country", "state"]
    search_fields = ["name", "code", "city"]
    raw_id_fields = ["manager"]
    inlines = [ZoneInline]

    def zone_count(self, obj):
        return obj.zones.count()

    zone_count.short_description = "Zones"


class LocationInline(admin.TabularInline):
    model = Location
    extra = 0
    fields = ["aisle", "rack", "shelf", "position", "barcode", "is_active"]
    show_change_link = True


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "warehouse",
        "zone_type",
        "temperature_controlled",
        "is_active",
    ]
    list_filter = ["zone_type", "temperature_controlled", "is_active", "warehouse"]
    search_fields = ["name", "code"]
    inlines = [LocationInline]


class BinInline(admin.TabularInline):
    model = Bin
    extra = 0
    fields = ["code", "barcode", "bin_type", "max_items", "is_active"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = [
        "barcode",
        "zone",
        "aisle",
        "rack",
        "shelf",
        "position",
        "is_active",
    ]
    list_filter = ["zone__warehouse", "zone", "is_active", "aisle"]
    search_fields = ["barcode", "aisle", "rack", "shelf"]
    inlines = [BinInline]


@admin.register(Bin)
class BinAdmin(admin.ModelAdmin):
    list_display = ["barcode", "code", "location", "bin_type", "max_items", "is_active"]
    list_filter = ["bin_type", "is_active"]
    search_fields = ["barcode", "code"]
