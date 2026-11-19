"""Confirming a booking with a payment method, and InstaPay review."""
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from core.errors import BusinessError
from orders.charges import release_from_order
from orders.models import Order
from orders.photos import shrink

from . import wallet
from .models import Payment

METHODS = (Payment.Method.CASH, Payment.Method.INSTAPAY)


def confirm_with_payment(order, method, wallet_amount=0, proof_file=None):
    # The extra discount may have changed since the customer saw the price
    # (only one per order, the biggest). Save the new one first, then ask the
    # customer to look again instead of charging a different amount silently.
    if _refresh_discount(order):
        raise BusinessError("discount_changed", "الخصم على الطلب اتغير. راجع المبلغ الجديد وأكد تاني.", status=409)
    return _confirm(order, method, wallet_amount, proof_file)


@transaction.atomic
def _refresh_discount(order):
    from orders import discounts

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING_PAYMENT:
        return False
    before = order.amount_due
    return discounts.refresh(order).amount_due != before


@transaction.atomic
def _confirm(order, method, wallet_amount=0, proof_file=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if method not in METHODS:
        raise BusinessError("payment_method_not_available", "طريقة الدفع دي مش متاحة.")
    if order.status != Order.Status.PENDING_PAYMENT:
        raise BusinessError("not_pending", "الطلب ده مش مستني تأكيد.")
    if order.hold_expires_at and order.hold_expires_at <= timezone.now():
        release_from_order(order)
        order.status = Order.Status.EXPIRED
        order.save(update_fields=["status", "updated_at"])
        raise BusinessError("hold_expired", "خلص وقت الحجز المؤقت. اختار الميعاد تاني.")

    from coupons.service import recheck_on_confirm

    recheck_on_confirm(order)
    wallet_amount = int(wallet_amount or 0)
    if wallet_amount < 0:
        raise BusinessError("bad_amount", "المبلغ مش صحيح.")
    wallet_amount = wallet.whole_pounds(wallet_amount)  # never pay piastres from the wallet
    if wallet_amount > wallet.max_usable_for(order.amount_due):
        raise BusinessError("wallet_over_limit", "مينفعش تدفع الجزء ده كله من المحفظة.")
    if method == Payment.Method.INSTAPAY and proof_file is None:
        raise BusinessError("proof_required", "ارفع صورة التحويل.")

    if wallet_amount:
        wallet.spend(order.customer, wallet_amount, order=order)
    if method == Payment.Method.INSTAPAY:
        jpeg, _ = shrink(proof_file.read())
        p = Payment(order=order, method=method, amount=order.amount_due - wallet_amount,
                    status=Payment.Status.PENDING_REVIEW)
        p.proof.save(f"{order.id}-{uuid.uuid4().hex}.jpg", ContentFile(jpeg), save=False)
        p.save()

    order.status = Order.Status.CONFIRMED
    order.payment_method = method
    order.wallet_used = wallet_amount
    order.hold_expires_at = None
    order.save(update_fields=["status", "payment_method", "wallet_used", "hold_expires_at", "updated_at"])
    from notifications import events

    events.booking_confirmed(order)
    if method == Payment.Method.INSTAPAY:
        events.instapay_to_review(order)
    return order


@transaction.atomic
def review_instapay(payment, manager, approve, reason=""):
    """Manager checks the transfer screenshot. Rejected = the technician collects cash instead."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.method != Payment.Method.INSTAPAY or payment.status != Payment.Status.PENDING_REVIEW:
        raise BusinessError("not_pending_review", "الدفعة دي مش مستنية مراجعة.")
    if not approve and not (reason or "").strip():
        raise BusinessError("reason_required", "اكتب سبب الرفض.")
    payment.status = Payment.Status.CONFIRMED if approve else Payment.Status.REJECTED
    payment.reviewed_by = manager
    payment.reviewed_at = timezone.now()
    payment.review_reason = (reason or "").strip()[:300]
    payment.save()
    return payment


@transaction.atomic
def mark_refunded(payment, manager):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != Payment.Status.REFUND_DUE:
        raise BusinessError("not_refund_due", "الدفعة دي مش مستنية استرجاع.")
    payment.status = Payment.Status.REFUNDED
    payment.reviewed_by = manager
    payment.reviewed_at = timezone.now()
    payment.save()
    return payment


def on_order_not_happening(order):
    """Cancelled / car not found: wallet part goes back to the wallet; InstaPay
    money is marked to be returned by the manager."""
    wallet.refund_order_spend(order)
    order.payments.filter(method=Payment.Method.INSTAPAY,
                          status__in=[Payment.Status.PENDING_REVIEW, Payment.Status.CONFIRMED]
                          ).update(status=Payment.Status.REFUND_DUE)


def record_cash(order, technician, amount):
    if amount:
        Payment.objects.create(order=order, method=Payment.Method.CASH, amount=amount,
                               status=Payment.Status.COLLECTED, collected_by=technician)
