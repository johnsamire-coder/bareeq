"""Applying a coupon to a held order, and the usage limits."""
from django.db import transaction
from django.utils import timezone

from core.errors import BusinessError
from core.money import whole_pound_discount
from orders import discounts
from orders.models import Order

from .models import Coupon, CouponUse

S = Order.Status
# A coupon is "used" by orders that were confirmed and are not cancelled.
COUNTED = (S.CONFIRMED, S.ON_THE_WAY, S.ARRIVED, S.IN_PROGRESS, S.COMPLETED)


def _used(coupon, customer=None, exclude_order=None):
    qs = CouponUse.objects.filter(coupon=coupon, order__status__in=COUNTED)
    if customer is not None:
        qs = qs.filter(customer=customer)
    if exclude_order is not None:
        qs = qs.exclude(order=exclude_order)
    return qs.count()


def check_limits(coupon, customer, order):
    if coupon.max_uses_total is not None and _used(coupon, exclude_order=order) >= coupon.max_uses_total:
        raise BusinessError("coupon_used_up", "الكود ده خلص عدد مرات استخدامه.")
    if _used(coupon, customer=customer, exclude_order=order) >= coupon.max_uses_per_customer:
        raise BusinessError("coupon_already_used", "إنت استخدمت الكود ده قبل كده.")


def coupon_discount(coupon, order):
    """On the services (oil is sold at cost, never discounted), whole pounds."""
    base = order.total - order.oil_total
    raw = base * coupon.value // 100 if coupon.kind == Coupon.Kind.PERCENT else min(coupon.value, base)
    return min(whole_pound_discount(base, raw), base)


@transaction.atomic
def apply_coupon(order, customer, code):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.customer_id != customer.id:
        raise BusinessError("not_your_order", "الطلب ده مش بتاعك.", status=403)
    if order.status != S.PENDING_PAYMENT:
        raise BusinessError("not_pending", "الكود بيتحط قبل تأكيد الحجز بس.")
    coupon = Coupon.objects.select_for_update().filter(code__iexact=(code or "").strip()).first()
    if coupon is None or not coupon.is_active:
        raise BusinessError("coupon_invalid", "الكود ده مش صحيح.")
    if coupon.expires_at <= timezone.now():
        raise BusinessError("coupon_expired", "الكود ده انتهى.")
    if coupon.zone_id and coupon.zone_id != order.zone_id:
        raise BusinessError("coupon_wrong_zone", "الكود ده مش متاح في منطقتك.")
    check_limits(coupon, customer, order)
    discount = coupon_discount(coupon, order)
    CouponUse.objects.update_or_create(order=order, defaults={"coupon": coupon, "customer": customer,
                                                              "discount": discount})
    discounts.refresh(order)
    if order.extra_discount_kind != "coupon":
        # Only one extra discount per order, and the other one is bigger.
        # Raising undoes the coupon (the whole function is one transaction).
        raise BusinessError(
            "better_discount",
            f"عندك خصم أكبر ({discounts.LABELS[order.extra_discount_kind]}: {order.extra_discount // 100} جنيه)، "
            "فالكود مش هيتطبق. الطلب بياخد خصم واحد بس، الأكبر.")
    return order


@transaction.atomic
def remove_coupon(order, customer):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.customer_id != customer.id:
        raise BusinessError("not_your_order", "الطلب ده مش بتاعك.", status=403)
    if order.status != S.PENDING_PAYMENT:
        raise BusinessError("not_pending", "الكود بيتشال قبل تأكيد الحجز بس.")
    CouponUse.objects.filter(order=order).delete()
    return discounts.refresh(order)


def recheck_on_confirm(order):
    """Two customers may hold the last use at the same time: the first to confirm wins."""
    use = CouponUse.objects.filter(order=order).select_related("coupon").first()
    if use is None:
        return
    coupon = Coupon.objects.select_for_update().get(pk=use.coupon_id)
    if coupon.expires_at <= timezone.now() or not coupon.is_active:
        raise BusinessError("coupon_expired", "الكود ده انتهى. شيله وكمّل.")
    check_limits(coupon, order.customer, order)
