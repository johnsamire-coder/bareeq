"""Invoices: BR-<year>-<000001>, restarting every year, never skipping a number."""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.errors import BusinessError
from orders.models import Order
from scheduling.availability import CAIRO

from .models import Invoice, InvoiceCounter, Payment


def _next_number(year):
    InvoiceCounter.objects.get_or_create(year=year)
    counter = InvoiceCounter.objects.select_for_update().get(year=year)
    counter.last_number += 1
    counter.save()
    return counter.last_number


def _paid(order, method, statuses):
    return order.payments.filter(method=method, status__in=statuses).aggregate(s=Sum("amount"))["s"] or 0


@transaction.atomic
def issue_invoice(order):
    """Called inside the same transaction that completes the order: if anything
    fails, the number is given back too, so there is never a gap."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.COMPLETED:
        raise BusinessError("not_completed", "الفاتورة بتتعمل بعد ما الشغل يخلص بس.")
    if order.invoices.filter(status=Invoice.Status.ISSUED).exists():
        raise BusinessError("already_invoiced", "الطلب ده ليه فاتورة بالفعل.")
    now = timezone.now()
    year = now.astimezone(CAIRO).year
    seq = _next_number(year)
    items = list(order.items.select_related("car__brand", "car__model"))
    lines = {
        "cars": [{
            "car": i.car.display_name,
            "services": [{"name": line["name"], "price": line["price"]} for line in i.quote["lines"]],
            "bundle": i.quote.get("bundle"),
            "discount": i.quote["discount"],
            "oil": i.quote.get("oil"),
        } for i in items],
        "charges": [{"label": c.get_kind_display(), "amount": c.amount, "source_order": c.source_order_id}
                    for c in order.applied_charges.filter(waived_at__isnull=True)],
    }
    lines["fees"] = [f for f in (
        {"label": "رسوم الطلب السريع", "amount": order.express_fee} if order.express_fee else None,
        {"label": f"رسوم المسافة ({order.distance_km} كيلو)", "amount": order.distance_fee} if order.distance_fee else None,
    ) if f]
    if order.extra_discount:
        from orders.discounts import LABELS

        use = getattr(order, "coupon_use", None)
        lines["extra_discount"] = {"kind": order.extra_discount_kind, "label": LABELS[order.extra_discount_kind],
                                   "code": use.coupon.code if order.extra_discount_kind == "coupon" and use else None,
                                   "discount": order.extra_discount}
    oil = sum((i.quote.get("oil") or {}).get("price", 0) for i in items)
    return Invoice.objects.create(
        order=order, number=f"BR-{year}-{seq:06d}", year=year, sequence=seq, issued_at=now, lines=lines,
        subtotal=order.subtotal - oil, discount=order.discount + order.extra_discount + order.rounding, oil_total=oil,
        charges_total=order.charges_total, fees_total=order.fees_total,
        total=order.amount_due, wallet_amount=order.wallet_used,
        instapay_amount=_paid(order, Payment.Method.INSTAPAY, [Payment.Status.PENDING_REVIEW, Payment.Status.CONFIRMED]),
        cash_amount=_paid(order, Payment.Method.CASH, [Payment.Status.COLLECTED]),
        card_amount=_paid(order, Payment.Method.CARD, [Payment.Status.CONFIRMED]),
    )


@transaction.atomic
def cancel_invoice(invoice, manager, reason):
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError("reason_required", "اكتب سبب إلغاء الفاتورة.")
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != Invoice.Status.ISSUED:
        raise BusinessError("already_cancelled", "الفاتورة دي ملغية بالفعل.")
    invoice.status = Invoice.Status.CANCELLED
    invoice.cancelled_at = timezone.now()
    invoice.cancelled_by = manager
    invoice.cancel_reason = reason[:300]
    invoice.save()
    return invoice
