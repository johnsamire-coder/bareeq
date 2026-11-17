from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models

from places.models import LAT_VALIDATORS, LNG_VALIDATORS, Zone


class TechnicianProfile(models.Model):
    """Where a technician works and where his day starts."""

    user = models.OneToOneField(
        django_settings.AUTH_USER_MODEL, verbose_name="الفني", on_delete=models.CASCADE,
        related_name="technician_profile", limit_choices_to={"role": "technician"},
    )
    zones = models.ManyToManyField(Zone, verbose_name="المناطق اللي بيغطيها", blank=True, related_name="technicians")
    start_label = models.CharField("نقطة البداية", max_length=100, blank=True, help_text="مثلاً: المحل، البيت")
    start_lat = models.DecimalField("خط العرض", max_digits=9, decimal_places=6, null=True, blank=True,
                                    validators=LAT_VALIDATORS)
    start_lng = models.DecimalField("خط الطول", max_digits=9, decimal_places=6, null=True, blank=True,
                                    validators=LNG_VALIDATORS)

    class Meta:
        verbose_name = "جدول فني"
        verbose_name_plural = "جداول الفنيين"

    def __str__(self):
        return str(self.user)

    @property
    def home(self):
        if self.start_lat is None or self.start_lng is None:
            return None
        return (self.start_lat, self.start_lng)


class WeeklyShift(models.Model):
    """Working hours for one weekday. No row for a weekday = weekly day off."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "الاتنين"
        TUESDAY = 1, "التلات"
        WEDNESDAY = 2, "الأربع"
        THURSDAY = 3, "الخميس"
        FRIDAY = 4, "الجمعة"
        SATURDAY = 5, "السبت"
        SUNDAY = 6, "الحد"

    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name="shifts")
    weekday = models.IntegerField("اليوم", choices=Weekday.choices)
    start_time = models.TimeField("من")
    end_time = models.TimeField("لحد")

    class Meta:
        unique_together = [("technician", "weekday")]
        ordering = ["technician", "weekday"]
        verbose_name = "مواعيد شغل"
        verbose_name_plural = "مواعيد الشغل"

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "وقت النهاية لازم يبقى بعد البداية."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DayOff(models.Model):
    """A specific date the technician does not work (leave, sickness...)."""

    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name="days_off")
    date = models.DateField("التاريخ")
    reason = models.CharField("السبب", max_length=200, blank=True)

    class Meta:
        unique_together = [("technician", "date")]
        ordering = ["date"]
        verbose_name = "إجازة"
        verbose_name_plural = "الإجازات"
