from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone


class Referral(models.Model):
    """A customer who signed up with a friend's code (SPEC 11).

    pending:  waiting for the new customer's first completed and paid order.
    credited: the friend got the wallet credit.
    review:   above the monthly limit, the manager decides.
    rejected: no credit (same address / car / phone as the friend, or the manager said no).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "مستني أول طلب"
        CREDITED = "credited", "نزل الرصيد"
        REVIEW = "review", "مستني المدير"
        REJECTED = "rejected", "مفيش مكافأة"

    referee = models.OneToOneField(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="referral", verbose_name="العميل الجديد")
    referrer = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name="referrals_made", verbose_name="صاحب الكود")
    code = models.CharField("الكود", max_length=20)
    device_id = models.CharField("موبايل العميل الجديد وقت التسجيل", max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField("السبب", max_length=300, blank=True)
    first_order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="+", verbose_name="أول طلب")
    wallet_entry = models.ForeignKey("payments.WalletEntry", null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="+")
    decided_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.PROTECT, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "دعوة"
        verbose_name_plural = "الدعوات"
