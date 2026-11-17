from django.contrib import admin

from decimal import Decimal

from django import forms

from services.admin import PoundsField, to_piastres

from .models import DailyClosing, Invoice, Material, Payment, TechnicianCustody, WalletEntry


class _ReadOnly(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WalletEntry)
class WalletEntryAdmin(_ReadOnly):
    list_display = ("customer", "kind", "amount", "remaining", "expires_at", "order", "created_at")
    list_filter = ("kind",)
    search_fields = ("customer__phone",)


@admin.register(Payment)
class PaymentAdmin(_ReadOnly):
    list_display = ("order", "method", "amount", "status", "created_at", "reviewed_by")
    list_filter = ("method", "status")


@admin.register(Invoice)
class InvoiceAdmin(_ReadOnly):
    list_display = ("number", "order", "issued_at", "total", "status")
    list_filter = ("status", "year")
    search_fields = ("number",)


@admin.register(DailyClosing)
class DailyClosingAdmin(_ReadOnly):
    list_display = ("technician", "date", "cash_expected", "cash_handed", "difference", "status")
    list_filter = ("status",)


class MaterialForm(forms.ModelForm):
    price_pounds = PoundsField(label="سعر الوحدة بالجنيه")

    class Meta:
        model = Material
        fields = ["name", "unit", "sort_order", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["price_pounds"].initial = Decimal(self.instance.unit_cost) / 100

    def save(self, commit=True):
        self.instance.unit_cost = to_piastres(self.cleaned_data["price_pounds"])
        return super().save(commit)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    form = MaterialForm
    list_display = ("name", "unit", "unit_price", "is_active")

    @admin.display(description="سعر الوحدة")
    def unit_price(self, obj):
        return f"{obj.unit_cost / 100:g} ج.م"


@admin.register(TechnicianCustody)
class TechnicianCustodyAdmin(_ReadOnly):
    list_display = ("technician", "kind", "amount", "closing", "note", "created_by", "created_at")
    list_filter = ("kind",)
