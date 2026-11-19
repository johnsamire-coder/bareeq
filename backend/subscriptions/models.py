"""Monthly subscription (SPEC 14 phase 3; rules agreed with John 19 Nov 2026).

A plan = N washes a month with fixed services at X% off the normal price.
A subscription = one customer, one car, one address, the same weekday and
time every visit. Each month is a SubscriptionPeriod, paid in advance (card /
mobile wallet / InstaPay, part from the wallet; no cash). Each visit is a
normal Order linked to the period, so technicians, closings and reports work
as usual; its share of the price shows as a «الاشتراك» discount.
"""
from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    name = models.CharField("اسم الباقة", max_length=100)
    washes_per_month = models.PositiveIntegerField("عدد الغسلات في الشهر", default=4)
    services = models.ManyToManyField("services.Service", verbose_name="الخدمات في كل غسلة")
    discount_percent = models.PositiveIntegerField("الخصم عن السعر العادي %", default=15)
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("متاحة", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "باقة اشتراك"
        verbose_name_plural = "باقات الاشتراك"

    def __str__(self):
        return self.name


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "شغال"
        ENDED = "ended", "خلص"

    customer = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    car = models.ForeignKey("cars.CustomerCar", on_delete=models.PROTECT, related_name="+")
    address = models.ForeignKey("places.Address", on_delete=models.PROTECT, related_name="+")
    weekday = models.PositiveSmallIntegerField("اليوم (0 = الاتنين)")
    start_time = models.TimeField("الساعة")
    technician = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+", verbose_name="الفني المفضل")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    renew = models.BooleanField("بيتجدد", default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "اشتراك"
        verbose_name_plural = "الاشتراكات"


class SubscriptionPeriod(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "مستني الدفع"
        PAID = "paid", "اتدفع"
        EXPIRED = "expired", "اتلغى (مدفعش)"

    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="periods")
    number = models.PositiveIntegerField("رقم الشهر")
    start_date = models.DateField("من")
    end_date = models.DateField("لحد")
    price = models.PositiveIntegerField("السعر (قرش)")
    normal_price = models.PositiveIntegerField("السعر العادي من غير خصم (قرش)")
    wallet_used = models.PositiveIntegerField("من المحفظة (قرش)", default=0)
    payment_method = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    makeup_visits = models.PositiveIntegerField("زيارات الشركة لغتها ولسه متحجزتش", default=0)
    renewal_reminded_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["subscription", "number"]
        unique_together = [("subscription", "number")]
        verbose_name = "شهر اشتراك"
        verbose_name_plural = "شهور الاشتراك"
