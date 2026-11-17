from django.contrib import admin

from scheduling.models import ClosedDay

from .models import DamageReport, Rating, RatingTag


@admin.register(RatingTag)
class RatingTagAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("order", "stars", "technician", "zone", "call_requested", "created_at", "handled_at")
    list_filter = ("stars", "zone", "technician")


@admin.register(DamageReport)
class DamageReportAdmin(admin.ModelAdmin):
    list_display = ("order", "customer", "status", "created_at")
    list_filter = ("status",)


@admin.register(ClosedDay)
class ClosedDayAdmin(admin.ModelAdmin):
    """View only here: closing a day from the dashboard also cancels and notifies."""

    list_display = ("date", "zone", "reason", "created_by")

    def has_add_permission(self, request):
        return False
