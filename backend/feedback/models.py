from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone

from core.services import get_setting
from orders.models import Order
from places.models import Zone


class RatingTag(models.Model):
    name = models.CharField("الكلمة", max_length=60)
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("ظاهرة", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "كلمة تقييم سريعة"
        verbose_name_plural = "كلمات التقييم السريعة"

    def __str__(self):
        return self.name


class Rating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="rating")
    customer = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    technician = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="ratings_received")
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    stars = models.PositiveSmallIntegerField("النجوم")
    tags = models.ManyToManyField(RatingTag, blank=True)
    comment = models.CharField("التعليق", max_length=1000, blank=True)
    call_requested = models.BooleanField("العميل عايز حد يكلمه", default=False)
    created_at = models.DateTimeField(default=timezone.now)
    handled_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="+")
    handle_note = models.CharField("اتعمل إيه", max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"

    @property
    def is_bad(self):
        return self.stars <= get_setting("ratings-bad-max-stars")


class RatingPhoto(models.Model):
    rating = models.ForeignKey(Rating, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="rating-photos/")
    uploaded_at = models.DateTimeField(default=timezone.now)


class DamageReport(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "مفتوح"
        RESOLVED = "resolved", "اتقفل"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="damage_reports")
    customer = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    description = models.CharField("وصف الضرر", max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.PROTECT, related_name="+")
    resolution_note = models.CharField("اتعمل إيه", max_length=1000, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "بلاغ ضرر"
        verbose_name_plural = "بلاغات الضرر"


class DamagePhoto(models.Model):
    report = models.ForeignKey(DamageReport, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="damage-photos/")
    uploaded_at = models.DateTimeField(default=timezone.now)
