from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import HeardAboutOption, OtpRequest, TermsAcceptance, TermsVersion, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ("phone", "full_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("phone", "full_name")
    fieldsets = (
        (None, {"fields": ("phone", "full_name", "role", "is_active")}),
        ("التسجيل", {"fields": ("date_joined", "signup_device_type", "referral_code_entered", "heard_about")}),
        ("صفحة الإدارة", {"fields": ("is_staff", "is_superuser", "password", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"fields": ("phone", "full_name", "role", "password1", "password2")}),)
    readonly_fields = ("date_joined",)


@admin.register(HeardAboutOption)
class HeardAboutAdmin(admin.ModelAdmin):
    list_display = ("label", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(TermsVersion)
class TermsVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "created_at", "created_by")
    readonly_fields = ("version", "created_at", "created_by")

    def has_change_permission(self, request, obj=None):
        return obj is None  # published text is frozen; add a new version instead

    def get_changeform_initial_data(self, request):
        # Start the new version from the current text, so only the changes need typing.
        current = TermsVersion.current()
        return {"text": current.text} if current else {}

    def changelist_view(self, request, extra_context=None):
        from core.admin import warn_if_terms_outdated

        warn_if_terms_outdated(request)
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TermsAcceptance)
class TermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("user", "terms_version", "accepted_at")
    readonly_fields = ("user", "terms_version", "accepted_at")


@admin.register(OtpRequest)
class OtpRequestAdmin(admin.ModelAdmin):
    list_display = ("phone", "device_id", "created_at", "expires_at", "wrong_attempts", "used_at")
    readonly_fields = [f.name for f in OtpRequest._meta.fields]
    search_fields = ("phone",)

    def has_add_permission(self, request):
        return False
