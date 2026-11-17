from django.contrib import admin

from .models import Setting


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "value_type", "group", "updated_at")
    list_filter = ("group",)
    search_fields = ("key", "label")
    readonly_fields = ("key", "value_type", "updated_at", "updated_by")

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
