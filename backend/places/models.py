from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .geo import InvalidPolygon, point_in_polygon, validate_polygon

LAT_VALIDATORS = [MinValueValidator(-90), MaxValueValidator(90)]
LNG_VALIDATORS = [MinValueValidator(-180), MaxValueValidator(180)]


class Zone(models.Model):
    """A service area drawn on the map by the manager. An address belongs to
    the zone whose shape contains its pin."""

    name = models.CharField("اسم المنطقة", max_length=100, unique=True)
    polygon = models.JSONField("الحدود", help_text="قايمة نقط [خط العرض، خط الطول].")
    is_active = models.BooleanField("شغالة", default=True)
    sort_order = models.PositiveIntegerField(
        "الأولوية", default=0, help_text="لو منطقتين داخلين في بعض، الأقل رقماً هي اللي بتتحسب."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "منطقة"
        verbose_name_plural = "المناطق"

    def __str__(self):
        return self.name

    def clean(self):
        try:
            self.polygon = validate_polygon(self.polygon)
        except InvalidPolygon as e:
            raise ValidationError({"polygon": str(e)})

    def contains(self, lat, lng):
        return point_in_polygon(lat, lng, self.polygon)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        # Shapes changed: every saved address may now belong to another zone.
        from .services import recompute_address_zones

        recompute_address_zones()


class Address(models.Model):
    customer = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name="العميل", on_delete=models.CASCADE, related_name="addresses"
    )
    label = models.CharField("الاسم", max_length=50, help_text="مثلاً: البيت، الشغل")
    lat = models.DecimalField("خط العرض", max_digits=9, decimal_places=6, validators=LAT_VALIDATORS)
    lng = models.DecimalField("خط الطول", max_digits=9, decimal_places=6, validators=LNG_VALIDATORS)
    zone = models.ForeignKey(Zone, verbose_name="المنطقة", null=True, blank=True, on_delete=models.SET_NULL)
    street = models.CharField("الشارع / المنطقة", max_length=200, blank=True)
    building = models.CharField("رقم العمارة / الفيلا", max_length=50)
    floor = models.CharField("الدور", max_length=20, blank=True)
    apartment = models.CharField("الشقة", max_length=20, blank=True)
    landmark = models.CharField("علامة مميزة", max_length=200, blank=True)
    is_active = models.BooleanField("موجود", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "عنوان"
        verbose_name_plural = "العناوين"

    def __str__(self):
        return f"{self.label} - {self.customer}"


class AreaRequest(models.Model):
    """'Notify me when you arrive': a customer whose pin is outside every zone.
    The manager sees these as a demand list."""

    customer = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name="العميل", on_delete=models.CASCADE, related_name="area_requests"
    )
    lat = models.DecimalField("خط العرض", max_digits=9, decimal_places=6, validators=LAT_VALIDATORS)
    lng = models.DecimalField("خط الطول", max_digits=9, decimal_places=6, validators=LNG_VALIDATORS)
    area_name = models.CharField("اسم المنطقة (من العميل)", max_length=200, blank=True)
    created_at = models.DateTimeField("وقت الطلب", auto_now_add=True)
    notified_at = models.DateTimeField("اتبلغ إمتى", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب «بلغوني لما توصلوا»"
        verbose_name_plural = "طلبات «بلغوني لما توصلوا»"

    def __str__(self):
        return f"{self.customer} ({self.lat}, {self.lng})"
