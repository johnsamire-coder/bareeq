from django.contrib import admin

from .models import CarBrand, CarColor, CarModel, CustomerCar


class CarModelInline(admin.TabularInline):
    model = CarModel
    extra = 0
    fields = ("name", "size_class", "is_active")


@admin.register(CarBrand)
class CarBrandAdmin(admin.ModelAdmin):
    list_display = ("name_ar", "name_en", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("name_ar", "name_en")
    inlines = [CarModelInline]


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "size_class", "is_active")
    list_editable = ("size_class", "is_active")
    list_filter = ("size_class", "brand")
    search_fields = ("name", "brand__name_en", "brand__name_ar")


@admin.register(CarColor)
class CarColorAdmin(admin.ModelAdmin):
    list_display = ("name", "hex_code", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(CustomerCar)
class CustomerCarAdmin(admin.ModelAdmin):
    list_display = ("__str__", "size_class", "parking", "needs_review", "is_active")
    list_filter = ("needs_review", "size_class", "parking")
    search_fields = ("customer__phone", "customer__full_name", "plate_number", "unlisted_model_name")
    raw_id_fields = ("customer",)
