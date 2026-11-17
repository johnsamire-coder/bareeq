from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.services import get_setting


class SizeClass(models.TextChoices):
    """Price and duration follow the size; the customer is never asked it
    (except when his model is not in the list)."""

    HATCHBACK = "hatchback", "هاتشباك"
    SEDAN = "sedan", "سيدان"
    SUV = "suv", "SUV / عربية كبيرة"
    LUXURY = "luxury", "فاخرة"


class CarBrand(models.Model):
    name_en = models.CharField("الاسم بالإنجليزي", max_length=60, unique=True)
    name_ar = models.CharField("الاسم بالعربي", max_length=60)
    sort_order = models.PositiveIntegerField("الترتيب", default=100)
    is_active = models.BooleanField("ظاهرة للعملاء", default=True)

    class Meta:
        ordering = ["sort_order", "name_en"]
        verbose_name = "ماركة"
        verbose_name_plural = "الماركات"

    def __str__(self):
        return f"{self.name_ar} ({self.name_en})"


class CarModel(models.Model):
    brand = models.ForeignKey(CarBrand, verbose_name="الماركة", on_delete=models.PROTECT, related_name="models")
    name = models.CharField("الموديل", max_length=60)
    size_class = models.CharField("الحجم", max_length=20, choices=SizeClass.choices)
    is_active = models.BooleanField("ظاهر للعملاء", default=True)

    class Meta:
        ordering = ["brand__sort_order", "brand__name_en", "name"]
        unique_together = [("brand", "name")]
        verbose_name = "موديل"
        verbose_name_plural = "الموديلات"

    def __str__(self):
        return f"{self.brand.name_en} {self.name}"


class CarColor(models.Model):
    name = models.CharField("اللون", max_length=40, unique=True)
    hex_code = models.CharField("كود اللون", max_length=7, default="#FFFFFF")
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("ظاهر", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "لون"
        verbose_name_plural = "الألوان"

    def __str__(self):
        return self.name


def allowed_years():
    """Years the customer can pick, newest first. Both ends come from settings."""
    first = get_setting("cars-first-year")
    last = timezone.localdate().year + get_setting("cars-years-ahead")
    return list(range(last, first - 1, -1))


class CustomerCar(models.Model):
    class Parking(models.TextChoices):
        CLOSED_GARAGE = "closed_garage", "جراج مقفول"
        OPEN_GARAGE = "open_garage", "جراج مفتوح"
        STREET = "street", "في الشارع"

    customer = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name="العميل", on_delete=models.CASCADE, related_name="cars"
    )
    brand = models.ForeignKey(CarBrand, verbose_name="الماركة", on_delete=models.PROTECT)
    model = models.ForeignKey(CarModel, verbose_name="الموديل", null=True, blank=True, on_delete=models.PROTECT)
    # Filled only when the customer chose "my model isn't listed":
    unlisted_model_name = models.CharField("اسم الموديل (مش في القايمة)", max_length=60, blank=True)
    needs_review = models.BooleanField("محتاجة مراجعة المدير", default=False)
    size_class = models.CharField("الحجم", max_length=20, choices=SizeClass.choices)
    year = models.PositiveIntegerField("سنة الصنع")
    color = models.ForeignKey(CarColor, verbose_name="اللون", on_delete=models.PROTECT)
    plate_number = models.CharField("رقم اللوحة", max_length=20, blank=True)
    parking = models.CharField("بتتركن فين", max_length=20, choices=Parking.choices)
    is_active = models.BooleanField("موجودة", default=True)
    created_at = models.DateTimeField("اتضافت", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "عربية عميل"
        verbose_name_plural = "عربيات العملاء"

    def __str__(self):
        return f"{self.display_name} - {self.customer}"

    @property
    def display_name(self):
        model = self.model.name if self.model else self.unlisted_model_name
        return f"{self.brand.name_en} {model} {self.year}"

    def _year_changed(self):
        # An old car stays valid even if the manager later narrows the year range.
        if self._state.adding or not self.pk:
            return True
        return CustomerCar.objects.filter(pk=self.pk).values_list("year", flat=True).first() != self.year

    def clean(self):
        errors = {}
        if self.model_id and self.unlisted_model_name:
            errors["unlisted_model_name"] = "اختار موديل من القايمة أو اكتب اسمه، مش الاتنين."
        if not self.model_id and not self.unlisted_model_name.strip():
            errors["model"] = "اختار الموديل."
        if self.model_id and self.model.brand_id != self.brand_id:
            errors["model"] = "الموديل ده مش تبع الماركة دي."
        if self.year is not None and self._year_changed() and self.year not in allowed_years():
            errors["year"] = "سنة الصنع مش في القايمة."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Size always follows the catalog model when there is one.
        if self.model_id:
            self.size_class = self.model.size_class
            self.unlisted_model_name = ""
            self.needs_review = False
        else:
            self.needs_review = True
        self.full_clean()
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.needs_review:
            from notifications.events import car_model_to_review

            car_model_to_review(self)
