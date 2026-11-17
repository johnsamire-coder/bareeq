"""Wallet ledger: gift balance only (no top-up, no cash withdrawal)."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.errors import BusinessError
from core.services import get_setting

from .models import WalletEntry

K = WalletEntry.Kind


def _live_credits(customer, now, lock=False):
    qs = WalletEntry.objects.filter(customer=customer, kind__in=WalletEntry.CREDIT_KINDS, remaining__gt=0,
                                    expires_at__gt=now).order_by("expires_at", "id")
    return qs.select_for_update() if lock else qs


def balance(customer):
    return _live_credits(customer, timezone.now()).aggregate(s=Sum("remaining"))["s"] or 0


def max_usable_for(amount_due):
    """Most of an order that can be paid from the wallet (rounded down)."""
    return amount_due * get_setting("wallet-max-order-share-percent") // 100


def credit(customer, amount, kind, expires_at=None, order=None, created_by=None, note=""):
    if kind not in WalletEntry.CREDIT_KINDS:
        raise BusinessError("bad_kind", "نوع الحركة مش صحيح.")
    if not isinstance(amount, int) or amount <= 0:
        raise BusinessError("bad_amount", "المبلغ لازم يبقى أكبر من صفر.")
    if kind == K.MANUAL:
        if created_by is None or getattr(created_by, "role", None) != "manager":
            raise BusinessError("manager_only", "المدير بس اللي يضيف رصيد.")
        if not (note or "").strip():
            raise BusinessError("note_required", "لازم تكتب سبب إضافة الرصيد.")
    now = timezone.now()
    return WalletEntry.objects.create(
        customer=customer, kind=kind, amount=amount, remaining=amount,
        expires_at=expires_at or now + timedelta(days=get_setting("wallet-credit-expiry-days")),
        order=order, created_by=created_by, note=(note or "").strip()[:300], created_at=now,
    )


@transaction.atomic
def spend(customer, amount, order=None):
    if not isinstance(amount, int) or amount <= 0:
        raise BusinessError("bad_amount", "المبلغ لازم يبقى أكبر من صفر.")
    now = timezone.now()
    credits = list(_live_credits(customer, now, lock=True))
    if sum(c.remaining for c in credits) < amount:
        raise BusinessError("insufficient_wallet", "رصيد المحفظة مش كفاية.")
    left = amount
    for c in credits:  # soonest-expiring first
        take = min(c.remaining, left)
        c.remaining -= take
        c.save(update_fields=["remaining"])
        left -= take
        if left == 0:
            break
    return WalletEntry.objects.create(customer=customer, kind=K.SPEND, amount=-amount, order=order, created_at=now)


def refund_order_spend(order):
    """Order paid partly from the wallet did not happen: give the amount back once."""
    spent = -(WalletEntry.objects.filter(order=order, kind=K.SPEND).aggregate(s=Sum("amount"))["s"] or 0)
    refunded = WalletEntry.objects.filter(order=order, kind=K.REFUND).aggregate(s=Sum("amount"))["s"] or 0
    if spent - refunded > 0:
        return credit(order.customer, spent - refunded, K.REFUND, order=order, note=f"استرجاع طلب {order.id}")
    return None


@transaction.atomic
def expire_credits():
    """Write an 'expiry' row for what is left of every expired credit."""
    now = timezone.now()
    n = 0
    for c in WalletEntry.objects.select_for_update().filter(
        kind__in=WalletEntry.CREDIT_KINDS, remaining__gt=0, expires_at__lte=now
    ):
        WalletEntry.objects.create(customer=c.customer, kind=K.EXPIRY, amount=-c.remaining, source_credit=c,
                                   created_at=now)
        c.remaining = 0
        c.save(update_fields=["remaining"])
        n += 1
    return n
