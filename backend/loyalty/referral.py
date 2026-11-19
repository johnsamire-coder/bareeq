"""Invite a friend (SPEC 11, numbers agreed with John 19 Nov 2026).

Every customer has a fixed code. A new customer who signs up with it gets a
first-order discount (loyalty/discounts.py). The friend gets wallet credit only
after the new customer's first completed and fully paid order, and only if
they do not share an address, a car plate or a phone. Above the monthly limit
the manager approves or rejects.
"""
import secrets

from django.db import transaction
from django.utils import timezone

from accounts.models import OtpRequest, User
from core.errors import BusinessError
from core.services import get_setting
from scheduling.availability import CAIRO

from .models import Referral

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L
S = Referral.Status


def code_for(user):
    """The customer's own code; made the first time it is needed."""
    if not user.referral_code:
        for _ in range(20):
            code = "B" + "".join(secrets.choice(ALPHABET) for _ in range(6))
            if not User.objects.filter(referral_code=code).exists():
                user.referral_code = code
                user.save(update_fields=["referral_code"])
                break
    return user.referral_code


def find_referrer(code):
    code = (code or "").strip()
    if not code:
        return None
    return User.objects.filter(referral_code__iexact=code, role=User.Role.CUSTOMER, is_active=True).first()


def on_signup(new_user, code, device_id=""):
    """Called inside sign-up. A code that matches nobody is refused (the app shows why)."""
    code = (code or "").strip()
    if not code or not get_setting("referral-enabled"):
        return None
    referrer = find_referrer(code)
    if referrer is None or referrer.id == new_user.id:
        raise BusinessError("referral_code_invalid", "كود الدعوة ده مش صحيح. صححه أو سيبه فاضي.")
    return Referral.objects.create(referee=new_user, referrer=referrer, code=referrer.referral_code,
                                   device_id=(device_id or "")[:100])


def _plate(p):
    return "".join(ch for ch in (p or "") if ch.isalnum()).upper()


def fraud_reason(referral, order):
    """Why the friend should get nothing, or "" when everything looks fine."""
    from cars.models import CustomerCar
    from places.models import Address

    referrer, referee = referral.referrer, referral.referee
    # Same place: the order's pin within ~30 m of any address of the friend.
    for a in Address.objects.filter(customer=referrer):
        if abs(float(a.lat) - float(order.lat)) < 0.0003 and abs(float(a.lng) - float(order.lng)) < 0.0003:
            return "نفس العنوان بتاع صاحب الكود"
    plates = {_plate(c.plate_number) for c in CustomerCar.objects.filter(customer=referee)} - {""}
    if plates and any(_plate(c.plate_number) in plates for c in CustomerCar.objects.filter(customer=referrer)):
        return "نفس رقم العربية بتاعة صاحب الكود"
    dev = referral.device_id
    if dev and dev != "app" and OtpRequest.objects.filter(phone=referrer.phone, device_id=dev).exists():
        return "نفس الموبايل اللي صاحب الكود بيدخل منه"
    return ""


def _month_credits(referrer):
    now = timezone.now().astimezone(CAIRO)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return Referral.objects.filter(referrer=referrer, status=S.CREDITED, decided_at__gte=start).count()


def _credit(referral, by=None):
    from payments import wallet
    from payments.models import WalletEntry

    entry = wallet.credit(referral.referrer, get_setting("referral-referrer-credit"), WalletEntry.Kind.REFERRAL,
                          order=referral.first_order, note=f"دعوة {referral.referee.full_name}")
    referral.status, referral.wallet_entry = S.CREDITED, entry
    referral.decided_by, referral.decided_at = by, timezone.now()
    referral.save()
    return referral


def after_paid_order(order):
    """The new customer's first completed and paid order: reward the friend (once)."""
    referral = Referral.objects.select_for_update().filter(referee=order.customer, status=S.PENDING).first()
    if referral is None:
        return None
    from orders.models import Order

    earlier = Order.objects.filter(customer=order.customer, status=Order.Status.COMPLETED,
                                   actual_end__lt=order.actual_end).exclude(pk=order.pk).exists()
    referral.first_order = order
    if earlier:
        referral.status, referral.reason = S.REJECTED, "مش أول طلب"
    elif reason := fraud_reason(referral, order):
        referral.status, referral.reason = S.REJECTED, reason
    elif _month_credits(referral.referrer) >= get_setting("referral-monthly-cap"):
        referral.status, referral.reason = S.REVIEW, "عدّى الحد الشهري"
        referral.save()
        from notifications.service import notify_managers

        notify_managers("referral_to_review", "دعوة محتاجة موافقتك",
                        f"{referral.referrer.full_name} عدّى الحد الشهري للدعوات.", {"referral": referral.id})
        return referral
    else:
        return _credit(referral)
    referral.decided_at = timezone.now()
    referral.save()
    return referral


@transaction.atomic
def approve(referral, manager):
    referral = Referral.objects.select_for_update().get(pk=referral.pk)
    if referral.status != S.REVIEW:
        raise BusinessError("not_in_review", "الدعوة دي مش مستنية موافقة.")
    return _credit(referral, by=manager)


@transaction.atomic
def reject(referral, manager, reason):
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError("reason_required", "اكتب سبب الرفض.")
    referral = Referral.objects.select_for_update().get(pk=referral.pk)
    if referral.status != S.REVIEW:
        raise BusinessError("not_in_review", "الدعوة دي مش مستنية موافقة.")
    referral.status, referral.reason = S.REJECTED, reason[:300]
    referral.decided_by, referral.decided_at = manager, timezone.now()
    referral.save()
    return referral
