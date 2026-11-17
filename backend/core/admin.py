from django.contrib import admin, messages

from .models import Setting


def warn_if_terms_outdated(request):
    from accounts.services import terms_outdated_settings

    changed = terms_outdated_settings()
    if changed:
        names = "، ".join(s.label for s in changed)
        messages.warning(
            request,
            f"اتغيرت أرقام مكتوبة في الشروط ({names}). انشر نسخة شروط جديدة فيها الأرقام الجديدة "
            "من «نسخ الشروط» ← «إضافة».",
        )


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "value_type", "group", "mentioned_in_terms", "updated_at")
    list_filter = ("group", "mentioned_in_terms")
    search_fields = ("key", "label")
    readonly_fields = ("key", "value_type", "mentioned_in_terms", "updated_at", "value_changed_at", "updated_by")

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        warn_if_terms_outdated(request)
        return super().changelist_view(request, extra_context)

    def response_change(self, request, obj):
        warn_if_terms_outdated(request)
        return super().response_change(request, obj)
