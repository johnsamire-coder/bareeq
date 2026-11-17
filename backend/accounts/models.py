import hashlib
import hmac

from django.conf import settings as django_settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from .phone import normalize_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, full_name="", role="customer", password=None, **extra):
        user = self.model(phone=normalize_phone(phone), full_name=full_name, role=role, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, full_name="", password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(phone, full_name, role=User.Role.MANAGER, password=password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Everyone who logs in: customers, technicians, managers.

    Login is by phone number + one-time code. A password exists only for
    staff who open the Django admin page."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", "عميل"
        TECHNICIAN = "technician", "فني"
        MANAGER = "manager", "مدير"
        SUPERVISOR = "supervisor", "مشرف"

    class DeviceType(models.TextChoices):
        ANDROID = "android", "أندرويد"
        IOS = "ios", "آيفون"
        WEB = "web", "متصفح"
        UNKNOWN = "unknown", "مش معروف"

    phone = models.CharField("الموبايل", max_length=20, unique=True)
    full_name = models.CharField("الاسم", max_length=150, blank=True)
    role = models.CharField("الدور", max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_active = models.BooleanField("نشط", default=True)
    is_staff = models.BooleanField("يدخل صفحة الإدارة", default=False)
    date_joined = models.DateTimeField("تاريخ التسجيل", default=timezone.now)

    # Collected at sign-up (SPEC 2). Referral credit itself is phase 2.
    signup_device_type = models.CharField(
        "نوع الجهاز وقت التسجيل", max_length=10, choices=DeviceType.choices, default=DeviceType.UNKNOWN
    )
    referral_code_entered = models.CharField("كود الإحالة اللي كتبه", max_length=30, blank=True)
    heard_about = models.ForeignKey(
        "accounts.HeardAboutOption",
        verbose_name="عرفنا منين",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمين"

    def __str__(self):
        return f"{self.full_name or '-'} ({self.phone})"

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    @property
    def needs_terms_acceptance(self):
        current = TermsVersion.current()
        if current is None or self.role != self.Role.CUSTOMER:
            return False
        return not self.terms_acceptances.filter(terms_version=current).exists()


class HeardAboutOption(models.Model):
    """'How did you hear about us' list, editable by the manager."""

    label = models.CharField("الاختيار", max_length=100)
    sort_order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("ظاهر", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "اختيار «عرفتنا منين»"
        verbose_name_plural = "اختيارات «عرفتنا منين»"

    def __str__(self):
        return self.label


class TermsVersion(models.Model):
    """The terms and cancellation rules text. Every edit is a new version, so we
    always know exactly which text each customer agreed to."""

    version = models.PositiveIntegerField("رقم النسخة", unique=True, editable=False)
    text = models.TextField("النص")
    created_at = models.DateTimeField("اتعملت", auto_now_add=True)
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-version"]
        verbose_name = "نسخة الشروط"
        verbose_name_plural = "نسخ الشروط"

    def __str__(self):
        return f"الشروط - نسخة {self.version}"

    @classmethod
    def current(cls):
        return cls.objects.order_by("-version").first()

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("A published terms version cannot be edited; publish a new version instead.")
        last = TermsVersion.objects.order_by("-version").values_list("version", flat=True).first() or 0
        self.version = last + 1
        super().save(*args, **kwargs)


class TermsAcceptance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="terms_acceptances")
    terms_version = models.ForeignKey(TermsVersion, on_delete=models.PROTECT, related_name="acceptances")
    accepted_at = models.DateTimeField("وقت الموافقة", default=timezone.now)

    class Meta:
        unique_together = [("user", "terms_version")]
        verbose_name = "موافقة على الشروط"
        verbose_name_plural = "الموافقات على الشروط"


def hash_code(phone, code):
    key = django_settings.SECRET_KEY.encode()
    return hmac.new(key, f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


class OtpRequest(models.Model):
    """One one-time code sent to a phone. The code itself is never stored, only its hash."""

    phone = models.CharField(max_length=20, db_index=True)
    device_id = models.CharField(max_length=100, blank=True, db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField()
    wrong_attempts = models.PositiveIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "كود دخول"
        verbose_name_plural = "أكواد الدخول"

    def matches(self, code):
        return hmac.compare_digest(self.code_hash, hash_code(self.phone, code))
