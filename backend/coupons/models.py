from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from places.models import Zone


class Coupon(models.Model):
    class Kind(models.TextChoices):
        PERCENT = "percent", "نسبة %"
        AMOUNT = "amount", "مبلغ ثابت"

    code = models.CharField("الكود", max_length=30, unique=True)
    kind = models.CharField("النوع", max_length=10, choices=Kind.choices)
    value = models.PositiveIntegerField("القيمة", help_text="نسبة من 1 لـ 100، أو مبلغ بالقرش")
    expires_at = models.DateTimeField("ينتهي")
    max_uses_total = models.PositiveIntegerField("أقصى عدد مرات لكل الناس", null=True, blank=True,
                                                 help_text="فاضي = من غير حد")
    max_uses_per_customer = models.PositiveIntegerField("أقصى عدد مرات لكل عميل", default=1)
    zone = models.ForeignKey(Zone, verbose_name="منطقة معينة", null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField("شغال", default=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "كوبون"
        verbose_name_plural = "الكوبونات"

    def __str__(self):
        return self.code

    def clean(self):
        self.code = (self.code or "").strip().upper()
        if not self.code:
            raise ValidationError({"code": "اكتب الكود."})
        if self.kind == self.Kind.PERCENT and not 1 <= self.value <= 100:
            raise ValidationError({"value": "النسبة من 1 لـ 100."})
        if self.kind == self.Kind.AMOUNT and self.value < 100:
            raise ValidationError({"value": "المبلغ لازم يبقى جنيه على الأقل."})
        if self.max_uses_per_customer < 1:
            raise ValidationError({"max_uses_per_customer": "لازم مرة واحدة على الأقل."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CouponUse(models.Model):
    """A coupon on an order. Counts as 'used' only once the order is confirmed
    and as long as it is not cancelled (see coupons.service.COUNTED)."""

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="coupon_use")
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="uses")
    customer = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    discount = models.PositiveIntegerField("الخصم (قرش)")
    created_at = models.DateTimeField(default=timezone.now)
