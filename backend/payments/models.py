from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone

from orders.models import Order


class WalletEntry(models.Model):
    """One change to a customer's wallet (gift balance). Never edited or deleted;
    only 'remaining' on a credit goes down as it is spent or expires."""

    class Kind(models.TextChoices):
        CASHBACK = "cashback", "كاش باك"
        REFERRAL = "referral", "مكافأة دعوة"
        REFUND = "refund", "استرجاع"
        MANUAL = "manual", "إضافة من المدير"
        SPEND = "spend", "استخدام في طلب"
        EXPIRY = "expiry", "انتهاء صلاحية"

    CREDIT_KINDS = (Kind.CASHBACK, Kind.REFERRAL, Kind.REFUND, Kind.MANUAL)

    customer = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name="wallet_entries")
    kind = models.CharField("النوع", max_length=20, choices=Kind.choices)
    amount = models.IntegerField("المبلغ (قرش، بالسالب للخصم)")
    remaining = models.IntegerField("الباقي من الرصيد ده", null=True, blank=True)
    expires_at = models.DateTimeField("ينتهي", null=True, blank=True)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name="wallet_entries")
    source_credit = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                   related_name="+")
    note = models.CharField("ملاحظة", max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "حركة محفظة"
        verbose_name_plural = "حركات المحفظة"

    def save(self, *args, **kwargs):
        if self.pk and list(kwargs.get("update_fields") or []) != ["remaining"]:
            raise ValueError("Wallet rows are never edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Wallet rows are never deleted.")


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "كاش"
        INSTAPAY = "instapay", "InstaPay"
        CARD = "card", "كارت / محفظة موبايل"

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "مستني تأكيد المدير"
        CONFIRMED = "confirmed", "اتأكد"
        REJECTED = "rejected", "اترفض"
        COLLECTED = "collected", "الفني استلمه"
        REFUND_DUE = "refund_due", "لازم يترجع للعميل"
        REFUNDED = "refunded", "اترجع"
        REFUNDED_TO_WALLET = "refunded_to_wallet", "دخل المحفظة"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=20, choices=Method.choices)
    amount = models.PositiveIntegerField("المبلغ (قرش)")
    status = models.CharField(max_length=20, choices=Status.choices)
    proof = models.ImageField("صورة التحويل", upload_to="instapay-proofs/", null=True, blank=True)
    collected_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.PROTECT, related_name="+")
    reviewed_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.PROTECT, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "دفعة"
        verbose_name_plural = "المدفوعات"


class InvoiceCounter(models.Model):
    """Last invoice number used in a year. Locked while a number is taken, inside
    the same database transaction, so numbers never skip or repeat."""

    year = models.PositiveIntegerField(primary_key=True)
    last_number = models.PositiveIntegerField(default=0)


class Invoice(models.Model):
    class Status(models.TextChoices):
        ISSUED = "issued", "سارية"
        CANCELLED = "cancelled", "ملغية"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField("رقم الفاتورة", max_length=20, unique=True)
    year = models.PositiveIntegerField()
    sequence = models.PositiveIntegerField()
    issued_at = models.DateTimeField()
    lines = models.JSONField("التفاصيل")
    subtotal = models.PositiveIntegerField("الخدمات قبل الخصم")
    discount = models.PositiveIntegerField("الخصم")
    oil_total = models.PositiveIntegerField("الزيت")
    charges_total = models.PositiveIntegerField("رسوم سابقة")
    total = models.PositiveIntegerField("الإجمالي المطلوب")
    wallet_amount = models.PositiveIntegerField("من المحفظة")
    instapay_amount = models.PositiveIntegerField("InstaPay")
    card_amount = models.PositiveIntegerField("كارت / محفظة موبايل", default=0)
    cash_amount = models.PositiveIntegerField("كاش")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.PROTECT, related_name="+")
    cancel_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-year", "-sequence"]
        unique_together = [("year", "sequence")]
        verbose_name = "فاتورة"
        verbose_name_plural = "الفواتير"

    def __str__(self):
        return self.number

    def delete(self, *args, **kwargs):
        raise ValueError("Invoices are never deleted; cancel them instead.")


class Material(models.Model):
    class Unit(models.TextChoices):
        LITER = "liter", "لتر"
        BOX = "box", "علبة"
        PIECE = "piece", "قطعة"

    name = models.CharField("الخامة", max_length=100)
    unit = models.CharField("الوحدة", max_length=10, choices=Unit.choices)
    unit_cost = models.PositiveIntegerField("سعر الوحدة (قرش)")
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("مستخدمة", default=True)
    is_provisional = models.BooleanField("تجريبي", default=False, help_text="سعر تجريبي لسه محتاج يتأكد.")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "خامة"
        verbose_name_plural = "الخامات"

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"


class MaterialUsage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="material_usages")
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    quantity = models.DecimalField("الكمية", max_digits=8, decimal_places=3)
    unit_cost = models.PositiveIntegerField("سعر الوحدة وقتها (قرش)")
    cost = models.PositiveIntegerField("التكلفة (قرش)")
    recorded_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "خامة مستخدمة"
        verbose_name_plural = "الخامات المستخدمة"


class DailyClosing(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "الفني سلّم"
        CONFIRMED = "confirmed", "المدير استلم"

    technician = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="closings")
    date = models.DateField("اليوم")
    cash_expected = models.IntegerField("الكاش اللي المفروض معاه (قرش)")
    cash_handed = models.IntegerField("الكاش اللي سلّمه (قرش)")
    difference = models.IntegerField("الفرق (قرش)")
    note = models.CharField("ملاحظة الفني", max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField()
    confirmed_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.PROTECT, related_name="+")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirm_reason = models.CharField("سبب الفرق (المدير)", max_length=300, blank=True)

    class Meta:
        unique_together = [("technician", "date")]
        ordering = ["-date"]
        verbose_name = "تقفيل يومي"
        verbose_name_plural = "التقفيل اليومي"


class TechnicianCustody(models.Model):
    """One immutable line in a technician's custody (عهدة) account.

    shortage: he handed over less cash than he collected (he owes it).
    overage: he handed over more (recorded; reduces what he owes).
    settlement: the manager recorded that he paid back / it was deducted.
    Balance = shortages - overages - settlements. Amounts are positive piastres."""

    class Kind(models.TextChoices):
        SHORTAGE = "shortage", "عجز"
        OVERAGE = "overage", "زيادة"
        SETTLEMENT = "settlement", "سداد"

    technician = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="custody_entries")
    closing = models.ForeignKey(DailyClosing, null=True, blank=True, on_delete=models.PROTECT,
                                related_name="custody_entries")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    amount = models.PositiveIntegerField("المبلغ (قرش)")
    note = models.CharField("السبب", max_length=300)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "عهدة فني"
        verbose_name_plural = "عهدة الفنيين"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Custody rows are never edited; add a new row instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Custody rows are never deleted.")


class OnlinePayment(models.Model):
    """One try to pay an order online (card or mobile wallet) through the payment
    company (phase 3). The order is confirmed only when the company itself tells
    us the money was taken (a signed message), never from the app."""

    class Status(models.TextChoices):
        CREATED = "created", "مستني الدفع"
        PAID = "paid", "اتدفع"
        FAILED = "failed", "مكملش"
        LATE = "late", "اتدفع بعد ما الحجز خلص (لازم يترجع)"

    ref = models.CharField("رقم العملية عندنا", max_length=40, unique=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="online_payments")
    provider = models.CharField("شركة الدفع", max_length=30)
    amount = models.PositiveIntegerField("المبلغ (قرش)")
    wallet_amount = models.PositiveIntegerField("من المحفظة (قرش)", default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    provider_txn_id = models.CharField("رقم العملية عند شركة الدفع", max_length=100, blank=True)
    callback_data = models.JSONField("رد شركة الدفع", default=dict, blank=True)
    note = models.CharField(max_length=300, blank=True)
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "دفع أونلاين"
        verbose_name_plural = "الدفع الأونلاين"
