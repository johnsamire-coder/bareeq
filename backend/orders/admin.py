from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("car", "size_class", "minutes", "total", "quote")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "scheduled_start", "technician", "zone", "status", "total")
    list_filter = ("status", "zone", "technician")
    search_fields = ("customer__phone", "customer__full_name")
    raw_id_fields = ("customer", "address", "technician")
    date_hierarchy = "scheduled_start"
    inlines = [OrderItemInline]
