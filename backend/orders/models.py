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
    charges_total = models.PositiveIntegerField("رسوم سابقة مضافة (قرش)", default=0)
    wallet_used = models.PositiveIntegerField("من المحفظة (قرش)", default=0)
    # Only ONE extra discount per order on top of the bundle: the biggest of
    # coupon / wash card / referral first order (orders/discounts.py).
    extra_discount_kind = models.CharField("نوع الخصم الإضافي", max_length=20, blank=True,
                                           choices=[("coupon", "كوبون"), ("wash_card", "كارت الغسيل"),
                                                    ("referral", "خصم أول طلب (دعوة)"),
                                                    ("subscription", "الاشتراك")])
    extra_discount = models.PositiveIntegerField("الخصم الإضافي (قرش)", default=0)
    materials_cost = models.PositiveIntegerField("تكلفة الخامات (قرش)", default=0)
    # A visit of a monthly subscription (phase 3): paid with the subscription.
    subscription_period = models.ForeignKey("subscriptions.SubscriptionPeriod", null=True, blank=True,
                                            on_delete=models.PROTECT, related_name="visits")
    actual_start = models.DateTimeField("بدأ فعلاً", null=True, blank=True)
    actual_end = models.DateTimeField("خلص فعلاً", null=True, blank=True)
    called_customer_at = models.DateTimeField("الفني كلم العميل", null=True, blank=True)
    cancel_reason = models.CharField("سبب الإلغاء", max_length=300, blank=True)
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
    def rounding(self):
        """Piastres taken off so the customer always pays whole pounds (only
        happens when an added fee has piastres; prices are already whole)."""
        from core.money import whole_pound_discount

        return whole_pound_discount(self.total - self.extra_discount + self.charges_total, 0)

    @property
    def amount_due(self):
        """Services total - extra discount + older unpaid fees added to this order, in whole pounds."""
        return self.total - self.extra_discount + self.charges_total - self.rounding

    @property
    def oil_total(self):
        return sum((i.quote.get("oil") or {}).get("price", 0) for i in self.items.all())

    @property
    def amount_to_collect(self):
        """What the technician still has to collect in cash."""
        from payments.models import Payment

        instapay = sum(p.amount for p in self.payments.filter(
            method__in=[Payment.Method.INSTAPAY, Payment.Method.CARD],
            status__in=[Payment.Status.PENDING_REVIEW, Payment.Status.CONFIRMED]))
        return max(0, self.amount_due - self.wallet_used - instapay)

    @property
    def wash_margin(self):
        """«هامش الغسلة»: services income minus oil (sold at cost) minus materials.
        Technician pay and fuel are NOT included, so this is not profit."""
        return self.total - self.oil_total - self.materials_cost

    @property
    def revenue(self):
        """«الإيراد»: everything the order is worth (services + oil + older fees)."""
        return self.amount_due

    @property
    def collected(self):
        """«اتحصّل فعلاً»: real money in: cash collected + confirmed InstaPay."""
        from payments.models import Payment

        return sum(p.amount for p in self.payments.filter(
            status__in=[Payment.Status.COLLECTED, Payment.Status.CONFIRMED]))

    @property
    def uncollected(self):
        """Revenue - collected - wallet. Zero when fully paid; above zero = still missing
        (InstaPay waiting for review, or the technician collected less)."""
        return self.revenue - self.collected - self.wallet_used

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


class OrderEvent(models.Model):
    """Every status change: who, when, where."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                           related_name="+")
    at = models.DateTimeField(default=timezone.now)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["at", "id"]
        verbose_name = "حركة على الطلب"
        verbose_name_plural = "حركات الطلبات"


def photo_path(instance, filename):
    return f"order-photos/{instance.order_id}/{filename}"


class OrderPhoto(models.Model):
    """Before/after photo, kept as evidence. Never deleted; a retake adds a new row."""

    class Stage(models.TextChoices):
        BEFORE = "before", "قبل"
        AFTER = "after", "بعد"

    class Side(models.TextChoices):
        FRONT = "front", "قدام"
        BACK = "back", "ورا"
        LEFT = "left", "الجنب الشمال"
        RIGHT = "right", "الجنب اليمين"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="photos")
    stage = models.CharField(max_length=10, choices=Stage.choices)
    side = models.CharField(max_length=10, choices=Side.choices)
    image = models.ImageField(upload_to=photo_path)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    taken_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    captured_at = models.DateTimeField("وقت التصوير (من موبايل الفني)")
    uploaded_at = models.DateTimeField("وقت الوصول للسيرفر")
    lat = models.DecimalField("خط العرض وقت التصوير", max_digits=9, decimal_places=6)
    lng = models.DecimalField("خط الطول وقت التصوير", max_digits=9, decimal_places=6)
    accuracy_m = models.PositiveIntegerField("دقة المكان (متر)", null=True, blank=True)
    original_sha256 = models.CharField("بصمة الملف الأصلي", max_length=64)
    flags = models.JSONField("ملاحظات", default=list, blank=True)

    class Meta:
        ordering = ["order", "stage", "side", "uploaded_at"]
        verbose_name = "صورة"
        verbose_name_plural = "صور قبل وبعد"


class CustomerCharge(models.Model):
    """A fee owed by the customer (late cancel / reschedule, car not found).
    Added as its own line to his next order; the manager may waive it."""

    class Kind(models.TextChoices):
        LATE_CANCELLATION = "late_cancellation", "إلغاء متأخر"
        LATE_RESCHEDULE = "late_reschedule", "تأجيل متأخر"
        CAR_NOT_FOUND = "car_not_found", "الفني ملقاش العربية"

    customer = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="charges")
    kind = models.CharField("النوع", max_length=30, choices=Kind.choices)
    amount = models.PositiveIntegerField("المبلغ (قرش)")
    source_order = models.ForeignKey(Order, verbose_name="بسبب طلب", on_delete=models.PROTECT,
                                     related_name="caused_charges")
    created_at = models.DateTimeField(default=timezone.now)
    applied_to_order = models.ForeignKey(Order, verbose_name="مضافة على طلب", null=True, blank=True,
                                         on_delete=models.SET_NULL, related_name="applied_charges")
    waived_at = models.DateTimeField("اتلغت إمتى", null=True, blank=True)
    waived_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, verbose_name="لغاها", null=True, blank=True,
                                  on_delete=models.PROTECT, related_name="+")
    waive_reason = models.CharField("سبب الإلغاء", max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "رسوم على عميل"
        verbose_name_plural = "رسوم على العملاء"
