from django.conf import settings as django_settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from cars.models import CustomerCar, SizeClass
from places.models import Address, Zone


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "مستني الدفع (الميعاد محجوز مؤقتاً)"
        CONFIRMED = "confirmed", "اتأكد"
        ON_THE_WAY = "on_the_way", "الفني في الطريق"
        ARRIVED = "arrived", "الفني وصل"
        IN_PROGRESS = "in_progress", "الشغل شغال"
        COMPLETED = "completed", "خلص"
        CANCELLED_BY_CUSTOMER = "cancelled_by_customer", "العميل لغاه"
        CANCELLED_BY_COMPANY = "cancelled_by_company", "الشركة لغته"
        CAR_NOT_FOUND = "car_not_found", "العربية مش موجودة"
        EXPIRED = "expired", "الحجز المؤقت خلص من غير دفع"

    # Statuses that never hold a technician's time.
    FREE_STATUSES = (Status.CANCELLED_BY_CUSTOMER, Status.CANCELLED_BY_COMPANY, Status.EXPIRED)

    customer = models.ForeignKey(django_settings.AUTH_USER_MODEL, verbose_name="العميل", on_delete=models.PROTECT,
                                 related_name="orders")
    address = models.ForeignKey(Address, verbose_name="العنوان", on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, verbose_name="المنطقة", on_delete=models.PROTECT)
    # Pin at booking time (the customer may move the saved address later).
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    technician = models.ForeignKey(django_settings.AUTH_USER_MODEL, verbose_name="الفني", null=True, blank=True,
                                   on_delete=models.PROTECT, related_name="jobs")
    scheduled_start = models.DateTimeField("الميعاد")
    scheduled_end = models.DateTimeField("النهاية المتوقعة")
    total_minutes = models.PositiveIntegerField("المدة (دقايق)")
    status = models.CharField("الحالة", max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT)
    hold_expires_at = models.DateTimeField("الحجز المؤقت لحد", null=True, blank=True)
    payment_method = models.CharField("طريقة الدفع", max_length=20, blank=True)
    subtotal = models.PositiveIntegerField("قبل الخصم (قرش)")
    discount = models.PositiveIntegerField("الخصم (قرش)", default=0)
    total = models.PositiveIntegerField("الإجمالي (قرش)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_start"]
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"
        indexes = [models.Index(fields=["technician", "scheduled_start"])]

    def __str__(self):
        return f"طلب {self.id} - {self.customer}"

    @property
    def place(self):
        return (self.lat, self.lng)

    @classmethod
    def blocking(cls, now=None):
        """Orders that hold a technician's time: everything except cancelled /
        expired, and except holds whose 10 minutes ran out."""
        now = now or timezone.now()
        return cls.objects.exclude(status__in=cls.FREE_STATUSES).exclude(
            Q(status=cls.Status.PENDING_PAYMENT) & Q(hold_expires_at__lte=now)
        )


class OrderItem(models.Model):
    """One car in the order, with its services and price as quoted at booking."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    car = models.ForeignKey(CustomerCar, verbose_name="العربية", on_delete=models.PROTECT)
    size_class = models.CharField(max_length=20, choices=SizeClass.choices)
    quote = models.JSONField("تفاصيل السعر")
    minutes = models.PositiveIntegerField()
    total = models.PositiveIntegerField("الإجمالي (قرش)")

    class Meta:
        verbose_name = "عربية في الطلب"
        verbose_name_plural = "العربيات في الطلب"
