from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models


class Setting(models.Model):
    """One business number or text that the manager can edit from the dashboard.

    Every business rule (buffers, gaps, holds, wallet rules, ...) lives here,
    never hard-coded. Money is always stored as integer piastres.
    """

    class ValueType(models.TextChoices):
        INTEGER = "integer", "رقم صحيح"
        MINUTES = "minutes", "دقايق"
        HOURS = "hours", "ساعات"
        DAYS = "days", "أيام"
        PERCENT = "percent", "نسبة مئوية"
        MONEY = "money", "فلوس (بالقرش)"
        BOOLEAN = "boolean", "نعم / لا"
        TEXT = "text", "نص"

    key = models.SlugField("المفتاح", max_length=100, unique=True)
    group = models.CharField("المجموعة", max_length=50)
    label = models.CharField("الاسم", max_length=200)
    description = models.TextField("الشرح", blank=True)
    value_type = models.CharField("النوع", max_length=20, choices=ValueType.choices)
    value = models.JSONField("القيمة")
    updated_at = models.DateTimeField("آخر تعديل", auto_now=True)
    updated_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        verbose_name="عدّلها",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["group", "key"]
        verbose_name = "إعداد"
        verbose_name_plural = "الإعدادات"

    def __str__(self):
        return f"{self.label} ({self.key})"

    NUMERIC_TYPES = {
        ValueType.INTEGER,
        ValueType.MINUTES,
        ValueType.HOURS,
        ValueType.DAYS,
        ValueType.PERCENT,
        ValueType.MONEY,
    }

    def clean(self):
        v = self.value
        if self.value_type in self.NUMERIC_TYPES:
            # bool is a subclass of int in Python, so reject it explicitly.
            if isinstance(v, bool) or not isinstance(v, int):
                raise ValidationError({"value": "لازم تكون رقم صحيح من غير كسور."})
            if v < 0:
                raise ValidationError({"value": "مينفعش تكون بالسالب."})
            if self.value_type == self.ValueType.PERCENT and v > 100:
                raise ValidationError({"value": "النسبة لازم تكون من 0 لـ 100."})
        elif self.value_type == self.ValueType.BOOLEAN:
            if not isinstance(v, bool):
                raise ValidationError({"value": "لازم تكون نعم أو لا."})
        elif self.value_type == self.ValueType.TEXT:
            if not isinstance(v, str):
                raise ValidationError({"value": "لازم تكون نص."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
