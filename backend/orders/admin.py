from django.contrib import admin

from .models import CustomerCharge, Order, OrderEvent, OrderItem, OrderPhoto


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


@admin.register(OrderPhoto)
class OrderPhotoAdmin(admin.ModelAdmin):
    list_display = ("order", "stage", "side", "captured_at", "uploaded_at", "flags", "taken_by")
    list_filter = ("stage",)
    readonly_fields = [f.name for f in OrderPhoto._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False  # evidence


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "by", "at", "note")
    readonly_fields = [f.name for f in OrderEvent._meta.fields]


@admin.register(CustomerCharge)
class CustomerChargeAdmin(admin.ModelAdmin):
    list_display = ("customer", "kind", "amount", "created_at", "applied_to_order", "waived_at", "waived_by")
    list_filter = ("kind",)
    readonly_fields = [f.name for f in CustomerCharge._meta.fields]  # waive from the dashboard (needs a reason)
