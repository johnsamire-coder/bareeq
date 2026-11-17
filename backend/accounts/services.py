import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.models import Setting
from core.services import get_setting

from .models import OtpRequest, TermsAcceptance, TermsVersion, User, hash_code
from .otp_senders import get_otp_sender
from .phone import normalize_phone


class OtpError(Exception):
    """A login problem shown to the user. `code` is a stable name the app can check."""

    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def request_otp(phone, device_id=""):
    phone = normalize_phone(phone)
    now = timezone.now()
    hour_ago = now - timedelta(hours=1)

    if OtpRequest.objects.filter(phone=phone, created_at__gte=hour_ago).count() >= get_setting(
        "otp-max-requests-per-phone-per-hour"
    ):
        raise OtpError("too_many_requests", "طلبت كود كتير. استنى شوية وجرب تاني.", status=429)
    if device_id and OtpRequest.objects.filter(device_id=device_id, created_at__gte=hour_ago).count() >= get_setting(
        "otp-max-requests-per-device-per-hour"
    ):
        raise OtpError("too_many_requests", "طلبت كود كتير. استنى شوية وجرب تاني.", status=429)

    code = f"{secrets.randbelow(1_000_000):06d}"
    OtpRequest.objects.create(
        phone=phone,
        device_id=device_id or "",
        code_hash=hash_code(phone, code),
        created_at=now,
        expires_at=now + timedelta(minutes=get_setting("otp-code-valid-minutes")),
    )
    get_otp_sender().send(phone, code)
    # Test mode: the code is also shown on the login screen (no SMS company yet).
    return code if get_setting("demo-mode") else None


def _check_code(phone, code):
    otp = (
        OtpRequest.objects.select_for_update()
        .filter(phone=phone, used_at__isnull=True, expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise OtpError("code_expired", "الكود انتهى. اطلب كود جديد.")
    if otp.wrong_attempts >= get_setting("otp-max-wrong-attempts"):
        raise OtpError("too_many_attempts", "جربت كود غلط كذا مرة. اطلب كود جديد.")
    if not otp.matches(str(code).strip()):
        otp.wrong_attempts += 1
        otp.save(update_fields=["wrong_attempts"])
        # Returned, not raised, so the counter is saved (raising would undo it).
        return OtpError("wrong_code", "الكود غلط.")
    return otp


def verify_otp(phone, code, signup=None):
    """Check the code and return (user, is_new).

    An unknown phone becomes a new customer, but only if `signup` holds the
    full name and the accepted terms version. Otherwise 'signup_required' is
    raised and the code stays valid, so the app can ask for the name and
    send the same code again.
    """
    phone = normalize_phone(phone)
    signup = signup or {}
    with transaction.atomic():
        otp = _check_code(phone, code)
        if isinstance(otp, OtpError):
            wrong = otp
        else:
            wrong = None
            user, is_new = _finish_login(phone, otp, signup)
    if wrong:
        raise wrong
    return user, is_new


def _finish_login(phone, otp, signup):
    user = User.objects.filter(phone=phone).first()
    is_new = user is None

    if user is not None and not user.is_active:
        raise OtpError("account_disabled", "الحساب ده موقوف. كلم خدمة العملاء.", status=403)

    if is_new:
        full_name = (signup.get("full_name") or "").strip()
        terms_version = signup.get("terms_version")
        if not full_name or not terms_version:
            # Do not use up the code: the app will resend it with the sign-up data.
            raise OtpError("signup_required", "رقم جديد. اكتب اسمك ووافق على الشروط.")
        current = TermsVersion.current()
        if current is None:
            raise OtpError("terms_not_published", "التسجيل مقفول مؤقتاً. جرب كمان شوية.", status=503)
        if int(terms_version) != current.version:
            raise OtpError("terms_outdated", "الشروط اتحدثت. اقرا النسخة الجديدة ووافق عليها.")
        user = User.objects.create_user(
            phone,
            full_name=full_name,
            role=User.Role.CUSTOMER,
            signup_device_type=signup.get("device_type") or User.DeviceType.UNKNOWN,
            referral_code_entered=(signup.get("referral_code") or "").strip()[:30],
            heard_about=signup.get("heard_about"),
        )
        TermsAcceptance.objects.create(user=user, terms_version=current)
        from notifications.events import welcome

        welcome(user)

    otp.used_at = timezone.now()
    otp.save(update_fields=["used_at"])
    return user, is_new


def accept_current_terms(user, terms_version):
    current = TermsVersion.current()
    if current is None or int(terms_version) != current.version:
        raise OtpError("terms_outdated", "الشروط اتحدثت. اقرا النسخة الجديدة ووافق عليها.")
    TermsAcceptance.objects.get_or_create(user=user, terms_version=current)


def terms_outdated_settings():
    """Settings written in the terms whose value changed after the current
    terms version was published. Non-empty means: publish a new version."""
    current = TermsVersion.current()
    qs = Setting.objects.filter(mentioned_in_terms=True, value_changed_at__isnull=False)
    if current is not None:
        qs = qs.filter(value_changed_at__gt=current.created_at)
    return list(qs)
