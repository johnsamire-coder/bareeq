from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from cars.models import SizeClass
from places.models import Zone


class Service(models.Model):
    class Category(models.TextChoices):
        WASH = "wash", "الغسيل"
        DETAIL = "detail", "الديتيلنج والتلميع"
        EXTRA = "extra", "خدمات إضافية"

    code = models.SlugField("الكود", max_length=50, unique=True)
    name = models.CharField("الاسم", max_length=100)
    description = models.CharField("الوصف", max_length=300, blank=True)
    category = models.CharField("القسم", max_length=20, choices=Category.choices)
    price_depends_on_size = models.BooleanField(
        "السعر بيختلف بحجم العربية", default=True,
        help_text="للعرض بس. الأسعار نفسها متسجلة لكل حجم في جدول الأسعار.",
    )
    needs_shade = models.BooleanField(
        "محتاجة ضل", default=False, help_text="لو العربية بتتركن في الشارع، التطبيق بينبه أو بيمنع (حسب الإعدادات)."
    )
    replaces = models.ManyToManyField(
        "self", verbose_name="بتلغي الخدمات دي", symmetrical=False, blank=True, related_name="replaced_by",
        help_text="لو العميل اختار الخدمة دي، الخدمات دي بتتشال لوحدها.",
    )
    is_oil_change = models.BooleanField("تغيير زيت", default=False, help_text="بيظهر معاها اختيار نوع الزيت.")
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("ظاهرة للعملاء", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "خدمة"
        verbose_name_plural = "الخدمات"

    def __str__(self):
        return self.name


class ServicePrice(models.Model):
    """Price of one service, in one zone, for one car size. Stored in piastres."""

    service = models.ForeignKey(Service, verbose_name="الخدمة", on_delete=models.CASCADE, related_name="prices")
    zone = models.ForeignKey(Zone, verbose_name="المنطقة", on_delete=models.CASCADE, related_name="service_prices")
    size_class = models.CharField("الحجم", max_length=20, choices=SizeClass.choices)
    price = models.PositiveIntegerField("السعر (بالقرش)")
    is_provisional = models.BooleanField("مؤقت", default=False, help_text="سعر تجريبي لسه محتاج يتأكد.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("service", "zone", "size_class")]
        ordering = ["zone__sort_order", "service__sort_order", "size_class"]
        verbose_name = "سعر"
        verbose_name_plural = "الأسعار"

    def __str__(self):
        return f"{self.service} / {self.zone} / {self.get_size_class_display()}"


class ServiceDuration(models.Model):
    """How long one service takes for one car size, in minutes."""

    service = models.ForeignKey(Service, verbose_name="الخدمة", on_delete=models.CASCADE, related_name="durations")
    size_class = models.CharField("الحجم", max_length=20, choices=SizeClass.choices)
    minutes = models.PositiveIntegerField("المدة (دقايق)", validators=[MinValueValidator(1)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("service", "size_class")]
        ordering = ["service__sort_order", "size_class"]
        verbose_name = "مدة"
        verbose_name_plural = "المدد"

    def __str__(self):
        return f"{self.service} / {self.get_size_class_display()}: {self.minutes} د"


class Bundle(models.Model):
    """When the customer picks all services of a bundle, he gets its discount
    on those services. Only the best single bundle applies to an order."""

    name = models.CharField("الاسم", max_length=100)
    description = models.CharField("الوصف", max_length=300, blank=True)
    services = models.ManyToManyField(Service, verbose_name="الخدمات", related_name="bundles")
    discount_percent = models.PositiveIntegerField(
        "الخصم %", validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("شغالة", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "باقة"
        verbose_name_plural = "الباقات"

    def __str__(self):
        return f"{self.name} ({self.discount_percent}%)"


class OilType(models.Model):
    """Oil the company supplies at cost. Shown as a separate line from the labor price."""

    name = models.CharField("نوع الزيت", max_length=100)
    description = models.CharField("الوصف (اللزوجة، الكمية...)", max_length=200, blank=True)
    price = models.PositiveIntegerField("السعر (بالقرش)")
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("متاح", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "نوع زيت"
        verbose_name_plural = "أنواع الزيت"

    def __str__(self):
        return self.name
