from django.contrib import admin

from .models import Address, AreaRequest, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order", "updated_at")
    list_editable = ("is_active", "sort_order")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("label", "customer", "zone", "building", "is_active")
    list_filter = ("zone", "is_active")
    search_fields = ("customer__phone", "customer__full_name", "street", "landmark")
    raw_id_fields = ("customer",)
    readonly_fields = ("zone",)


@admin.register(AreaRequest)
class AreaRequestAdmin(admin.ModelAdmin):
    list_display = ("customer", "area_name", "lat", "lng", "created_at", "notified_at")
    search_fields = ("customer__phone", "area_name")
    raw_id_fields = ("customer",)
