"""Fees owed by a customer and how they ride on his next order."""
from django.db import transaction
from django.utils import timezone

from core.errors import BusinessError

from .models import CustomerCharge, Order


def outstanding_charges(customer):
    """Not waived and not sitting on a live order."""
    return list(CustomerCharge.objects.filter(customer=customer, waived_at__isnull=True,
                                              applied_to_order__isnull=True).order_by("created_at"))


def charges_payload(charges):
    return [{"id": c.id, "kind": c.kind, "label": c.get_kind_display(), "amount": c.amount,
             "source_order": c.source_order_id, "created_at": c.created_at} for c in charges]


def attach_to_order(order):
    charges = outstanding_charges(order.customer)
    if charges:
        CustomerCharge.objects.filter(pk__in=[c.pk for c in charges]).update(applied_to_order=order)
        order.charges_total = sum(c.amount for c in charges)
        order.save(update_fields=["charges_total", "updated_at"])
    return charges


def release_from_order(order):
    """The order will not happen: its added fees become outstanding again."""
    CustomerCharge.objects.filter(applied_to_order=order).update(applied_to_order=None)
    if order.charges_total:
        order.charges_total = 0
        order.save(update_fields=["charges_total", "updated_at"])


def add_charge(customer, kind, amount, source_order):
    if amount <= 0:
        return None
    return CustomerCharge.objects.create(customer=customer, kind=kind, amount=amount, source_order=source_order)


@transaction.atomic
def waive_charge(charge, manager, reason):
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError("reason_required", "لازم تكتب سبب إلغاء الرسوم.")
    charge = CustomerCharge.objects.select_for_update().get(pk=charge.pk)
    if charge.waived_at:
        raise BusinessError("already_waived", "الرسوم دي اتلغت قبل كده.")
    order = charge.applied_to_order
    if order is not None and order.status == Order.Status.COMPLETED:
        raise BusinessError("already_paid", "الرسوم دي اتدفعت مع طلب خلص.")
    if order is not None:
        order = Order.objects.select_for_update().get(pk=order.pk)
        order.charges_total = max(0, order.charges_total - charge.amount)
        order.save(update_fields=["charges_total", "updated_at"])
    charge.applied_to_order = None
    charge.waived_at = timezone.now()
    charge.waived_by = manager
    charge.waive_reason = reason
    charge.save()
    return charge
