"""Paying an order online (card / mobile wallet) through the payment company.

1. The customer presses «ادفع بالكارت»: start() checks everything, keeps the
   time slot a bit longer, and returns the payment company's page.
2. The company sends us a signed message (callback). Only then the order is
   confirmed, the wallet part is taken, and the money is recorded.
3. The same message twice changes nothing. A wrong amount or a bad signature
   is refused. Money that arrives after the booking was lost is marked
   «لازم يترجع» and the manager is told.
"""
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.errors import BusinessError
from core.services import get_setting
from orders.models import Order

from . import wallet
from .gateway import BadSignature, get_gateway
from .models import OnlinePayment, Payment

S = OnlinePayment.Status


def start(order, customer, wallet_amount=0):
    from .payments import _refresh_discount

    if not get_setting("card-payment-enabled"):
        raise BusinessError("payment_method_not_available", "الدفع بالكارت مش متاح دلوقتي.")
    if order.customer_id != customer.id:
        raise BusinessError("not_your_order", "الطلب ده مش بتاعك.", status=403)
    if order.subscription_period_id:
        raise BusinessError("pay_the_month", "زيارة الاشتراك بتتدفع مع الشهر كله من صفحة الاشتراك.")
    if _refresh_discount(order):
        raise BusinessError("discount_changed", "الخصم على الطلب اتغير. راجع المبلغ الجديد وأكد تاني.", status=409)
    return _start(order, wallet_amount)


@transaction.atomic
def _start(order, wallet_amount):
    from coupons.service import recheck_on_confirm

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING_PAYMENT:
        raise BusinessError("not_pending", "الطلب ده مش مستني تأكيد.")
    now = timezone.now()
    if order.hold_expires_at and order.hold_expires_at <= now:
        raise BusinessError("hold_expired", "خلص وقت الحجز المؤقت. اختار الميعاد تاني.")
    recheck_on_confirm(order)
    wallet_amount = wallet.whole_pounds(int(wallet_amount or 0))
    if wallet_amount < 0 or wallet_amount > wallet.max_usable_for(order.amount_due):
        raise BusinessError("wallet_over_limit", "مينفعش تدفع الجزء ده كله من المحفظة.")
    if wallet_amount > wallet.balance(order.customer):
        raise BusinessError("insufficient_wallet", "رصيد المحفظة مش كفاية.")
    amount = order.amount_due - wallet_amount
    if amount <= 0:
        raise BusinessError("nothing_to_pay", "مفيش مبلغ يتدفع أونلاين.")
    # Older unfinished tries of this order are left; only a signed answer counts.
    gw = get_gateway()
    payment = OnlinePayment.objects.create(ref=uuid.uuid4().hex, order=order, provider=gw.name, amount=amount,
                                           wallet_amount=wallet_amount)
    order.hold_expires_at = max(order.hold_expires_at or now, now) + timedelta(
        minutes=get_setting("card-payment-hold-extra-minutes"))
    order.save(update_fields=["hold_expires_at", "updated_at"])
    return payment


def handle_callback(provider, data):
    """The payment company's signed message. Returns the OnlinePayment."""
    try:
        result = get_gateway(provider).parse_callback(data)
    except (BadSignature, KeyError):
        raise BusinessError("bad_signature", "الرسالة دي مش من شركة الدفع.", status=403)
    return _apply(result, provider, data)


@transaction.atomic
def _apply(result, provider, data):
    payment = OnlinePayment.objects.select_for_update().filter(ref=result.ref, provider=provider).first()
    if payment is None:
        raise BusinessError("unknown_payment", "العملية دي مش عندنا.", status=404)
    if payment.status != S.CREATED:
        return payment  # already handled: the company may send the same message again
    payment.callback_data = data if isinstance(data, dict) else {}
    payment.provider_txn_id = (result.txn_id or "")[:100]
    payment.finished_at = timezone.now()
    if not result.paid:
        payment.status = S.FAILED
        payment.save()
        return payment
    if result.amount != payment.amount:
        payment.status, payment.note = S.FAILED, f"المبلغ اللي اتدفع ({result.amount}) غير المطلوب ({payment.amount})"
        payment.save()
        from notifications.service import notify_managers

        notify_managers("online_payment_problem", "مشكلة في دفع أونلاين",
                        f"طلب {payment.order_id}: {payment.note}. راجع شركة الدفع.", {"order": payment.order_id})
        return payment
    order = Order.objects.select_for_update().get(pk=payment.order_id)
    if payment.period_id:
        from subscriptions.service import online_paid

        if not online_paid(payment):
            return _late(payment, order, "شهر الاشتراك خلص وقت حجزه قبل ما الدفع يوصل")
        payment.status = S.PAID
        payment.save()
        return payment
    if order.status != Order.Status.PENDING_PAYMENT:
        return _late(payment, order)
    wallet_amount = payment.wallet_amount if payment.wallet_amount <= wallet.balance(order.customer) else 0
    if payment.wallet_amount and not wallet_amount:
        return _late(payment, order, "رصيد المحفظة اتغير قبل الدفع")
    if wallet_amount:
        wallet.spend(order.customer, wallet_amount, order=order)
    now = timezone.now()
    p = Payment.objects.create(order=order, method=Payment.Method.CARD, amount=payment.amount,
                               status=Payment.Status.CONFIRMED, reviewed_at=now)
    order.status = Order.Status.CONFIRMED
    order.payment_method = Payment.Method.CARD
    order.wallet_used = wallet_amount
    order.hold_expires_at = None
    order.save(update_fields=["status", "payment_method", "wallet_used", "hold_expires_at", "updated_at"])
    payment.status, payment.payment = S.PAID, p
    payment.save()
    from notifications import events

    events.booking_confirmed(order)
    return payment


def _late(payment, order, why="الحجز خلص أو اتلغى قبل ما الدفع يوصل"):
    """Money taken but the booking is gone: record it as money to give back."""
    p = Payment.objects.create(order=order, method=Payment.Method.CARD, amount=payment.amount,
                               status=Payment.Status.REFUND_DUE, reviewed_at=timezone.now())
    payment.status, payment.payment, payment.note = S.LATE, p, why
    payment.save()
    from notifications.service import notify_managers

    notify_managers("online_payment_problem", "فلوس لازم ترجع",
                    f"طلب {order.id}: {why}. المبلغ {payment.amount // 100} جنيه لازم يترجع للعميل.",
                    {"order": order.id})
    return payment


# ---------- giving card money back ----------

@transaction.atomic
def refund_to_card(payment):
    """Send a card payment marked «لازم يترجع» back through the payment company."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.method != Payment.Method.CARD or payment.status != Payment.Status.REFUND_DUE:
        raise BusinessError("not_refund_due", "الدفعة دي مش مستنية استرجاع.")
    attempt = OnlinePayment.objects.filter(payment=payment).first()
    if attempt is None:
        raise BusinessError("not_refund_due", "مش لاقيين عملية الدفع دي عند شركة الدفع.")
    get_gateway(attempt.provider).refund(attempt, payment.amount)
    payment.status, payment.reviewed_at = Payment.Status.REFUNDED, timezone.now()
    payment.save(update_fields=["status", "reviewed_at"])
    attempt.refunded_at = timezone.now()
    attempt.save(update_fields=["refunded_at"])
    return payment


def refund_order_to_card(order, customer):
    if order.customer_id != customer.id:
        raise BusinessError("not_your_order", "الطلب ده مش بتاعك.", status=403)
    due = list(order.payments.filter(method=Payment.Method.CARD, status=Payment.Status.REFUND_DUE))
    if not due:
        raise BusinessError("nothing_to_refund", "مفيش فلوس مستنية ترجع في الطلب ده.")
    return [refund_to_card(p) for p in due]


def auto_refund_cards():
    """Card money waiting more than the setting (the customer did not choose the
    wallet): goes back to the card by itself (run_scheduled_jobs)."""
    from django.db.models import Q

    hours = get_setting("card-refund-auto-after-hours")
    cutoff = timezone.now() - timedelta(hours=hours)
    n = 0
    for p in Payment.objects.filter(method=Payment.Method.CARD, status=Payment.Status.REFUND_DUE).filter(
            Q(order__updated_at__lte=cutoff)):
        try:
            refund_to_card(p)
            n += 1
        except BusinessError:
            pass
    return n
