from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """One message to one user: always in the in-app list, and pushed to the
    phone when Firebase is connected."""

    class PushStatus(models.TextChoices):
        NOT_CONFIGURED = "not_configured", "الإرسال للموبايل لسه مش متوصل"
        NO_DEVICE = "no_device", "مفيش موبايل متسجل"
        SENT = "sent", "اتبعت"
        FAILED = "failed", "فشل"

    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=500)
    data = models.JSONField(default=dict, blank=True, help_text="مثلاً {order, action}: الزرار اللي بيفتحه الإشعار")
    dedupe_key = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    push_status = models.CharField(max_length=20, choices=PushStatus.choices, default=PushStatus.NOT_CONFIGURED)
    push_error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "dedupe_key"], name="one_notification_per_key")]
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"


class DeviceToken(models.Model):
    """The phone's push address (Firebase token), sent by the app after login."""

    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    token = models.CharField(max_length=500, unique=True)
    platform = models.CharField(max_length=10, choices=[("android", "أندرويد"), ("ios", "آيفون"), ("web", "متصفح")])
    created_at = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
