"""Timed jobs. Each one can run many times: notifications carry a key so a
customer never gets the same reminder twice."""
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from core.services import get_setting
from orders.models import Order

from . import events


def booking_reminders():
    now = timezone.now()
    soon = now + timedelta(minutes=get_setting("notifications-reminder-minutes-before"))
    n = 0
    for o in Order.objects.filter(status=Order.Status.CONFIRMED, scheduled_start__gt=now, scheduled_start__lte=soon):
        events.booking_reminder(o)
        n += 1
    return n


def rating_reminders():
    cutoff = timezone.now() - timedelta(hours=get_setting("ratings-reminder-after-hours"))
    n = 0
    for o in Order.objects.filter(status=Order.Status.COMPLETED, actual_end__lte=cutoff, rating__isnull=True):
        events.rating_reminder(o)
        n += 1
    return n


def next_wash_reminders():
    now = timezone.now()
    cutoff = now - timedelta(days=get_setting("notifications-next-wash-after-days"))
    busy = Order.blocking().filter(scheduled_start__gt=now).values("customer")
    last = (Order.objects.filter(status=Order.Status.COMPLETED).exclude(customer__in=busy)
            .values("customer").annotate(last_end=Max("actual_end")).filter(last_end__lte=cutoff))
    n = 0
    for row in last:
        order = Order.objects.filter(customer=row["customer"], status=Order.Status.COMPLETED,
                                     actual_end=row["last_end"]).select_related("customer").first()
        events.next_wash(order.customer, order)
        n += 1
    return n


def wallet_expiry_reminders():
    from payments.models import WalletEntry

    now = timezone.now()
    horizon = now + timedelta(days=get_setting("wallet-expiry-reminder-days"))
    n = 0
    for e in WalletEntry.objects.filter(kind__in=WalletEntry.CREDIT_KINDS, remaining__gt=0, expires_at__gt=now,
                                        expires_at__lte=horizon).select_related("customer"):
        events.wallet_expiring(e)
        n += 1
    return n
