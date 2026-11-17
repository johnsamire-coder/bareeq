from decimal import ROUND_HALF_UP, Decimal

from django import forms
from django.contrib import admin, messages

from .models import Bundle, OilType, Service, ServiceDuration, ServicePrice


class PoundsField(forms.DecimalField):
    """Manager types pounds (e.g. 150 or 150.50); stored as piastres."""

    def __init__(self, **kwargs):
        super().__init__(min_value=0, max_digits=10, decimal_places=2, **kwargs)


def to_piastres(pounds):
    return int((Decimal(pounds) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class _PoundsForm(forms.ModelForm):
    price_pounds = PoundsField(label="السعر بالجنيه")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["price_pounds"].initial = Decimal(self.instance.price) / 100

    def save(self, commit=True):
        self.instance.price = to_piastres(self.cleaned_data["price_pounds"])
        return super().save(commit)


class ServicePriceForm(_PoundsForm):
    class Meta:
        model = ServicePrice
        fields = ["service", "zone", "size_class"]

    def save(self, commit=True):
        self.instance.is_provisional = False  # typed by the manager = confirmed
        return super().save(commit)


class OilTypeForm(_PoundsForm):
    class Meta:
        model = OilType
        fields = ["name", "description", "sort_order", "is_active"]


def pounds(obj):
    return f"{obj.price / 100:g} ج.م"


pounds.short_description = "السعر"


class DurationInline(admin.TabularInline):
    model = ServiceDuration
    extra = 0


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "needs_shade", "is_active", "sort_order")
    list_editable = ("needs_shade", "is_active", "sort_order")
    filter_horizontal = ("replaces",)
    inlines = [DurationInline]


@admin.action(description="تأكيد الأسعار المختارة (مش مؤقتة)")
def confirm_prices(modeladmin, request, queryset):
    n = queryset.update(is_provisional=False)
    messages.success(request, f"اتأكد {n} سعر.")


@admin.register(ServicePrice)
class ServicePriceAdmin(admin.ModelAdmin):
    form = ServicePriceForm
    list_display = ("service", "zone", "size_class", pounds, "is_provisional")
    list_filter = ("is_provisional", "zone", "size_class", "service")
    actions = [confirm_prices]

    def changelist_view(self, request, extra_context=None):
        n = ServicePrice.objects.filter(is_provisional=True).count()
        if n:
            messages.warning(
                request,
                f"تنبيه: {n} سعر لسه مؤقت (أسعار تجريبية من الديمو). عدّل السعر أو اختار الأسعار "
                "واستخدم «تأكيد الأسعار المختارة».",
            )
        return super().changelist_view(request, extra_context)


@admin.register(ServiceDuration)
class ServiceDurationAdmin(admin.ModelAdmin):
    list_display = ("service", "size_class", "minutes")
    list_editable = ("minutes",)
    list_filter = ("size_class", "service")


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "discount_percent", "is_active", "sort_order")
    list_editable = ("discount_percent", "is_active")
    filter_horizontal = ("services",)


@admin.register(OilType)
class OilTypeAdmin(admin.ModelAdmin):
    form = OilTypeForm
    list_display = ("name", "description", pounds, "is_active")
