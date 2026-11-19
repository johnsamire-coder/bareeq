from django.contrib import admin

from .models import Subscription, SubscriptionPeriod, SubscriptionPlan


@admin.register(SubscriptionPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "washes_per_month", "discount_percent", "is_active")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("customer", "plan", "car", "weekday", "start_time", "status", "renew")
    list_filter = ("status",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SubscriptionPeriod)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("subscription", "number", "start_date", "end_date", "price", "status")
    list_filter = ("status",)

    def has_delete_permission(self, request, obj=None):
        return False
