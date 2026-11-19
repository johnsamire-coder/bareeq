"""The extra discount on an order (agreed with John, 19 Nov 2026).

The bundle discount always applies (it is already inside the price quote).
On top of it the order gets only ONE of these, the biggest one:
  - a coupon the customer typed,
  - the wash card reward (every N washes),
  - the first-order discount of a customer invited by a friend.
All of them are on the services only (oil is sold at cost, never discounted),
and the customer always pays whole pounds (the piastres go into the discount).

Each kind registers a small function that says how much it would give this
order (0 = nothing). Later steps add the wash card and the referral.
"""
from core.money import whole_pound_discount

from .models import Order

# Shown to the customer and on the invoice.
LABELS = dict(Order._meta.get_field("extra_discount_kind").choices)

_PROVIDERS = {}  # kind -> function(order) -> piastres


def provider(kind):
    def register(fn):
        _PROVIDERS[kind] = fn
        return fn
    return register


def services_base(order):
    """What discounts can apply to: everything except the oil."""
    return order.total - order.oil_total


def capped(order, raw):
    """Never more than the services, and whole pounds."""
    base = services_base(order)
    raw = max(0, min(raw, base))
    return min(whole_pound_discount(base, raw), base)


def candidates(order):
    """{kind: amount} for every extra discount this order could get now."""
    out = {}
    for kind, fn in _PROVIDERS.items():
        amount = capped(order, fn(order) or 0)
        if amount > 0:
            out[kind] = amount
    return out


def best(order):
    """(kind, amount) of the biggest one; ("", 0) when there is none.
    On a tie the earlier kind in the list wins (coupon, wash card, referral)."""
    found = candidates(order)
    kind = None
    for k in LABELS:
        if k in found and (kind is None or found[k] > found[kind]):
            kind = k
    return (kind, found[kind]) if kind else ("", 0)


def refresh(order):
    """Put the best extra discount on the order and save. Returns the order."""
    kind, amount = best(order)
    if (order.extra_discount_kind, order.extra_discount) != (kind, amount):
        order.extra_discount_kind, order.extra_discount = kind, amount
        order.save(update_fields=["extra_discount_kind", "extra_discount", "updated_at"])
    return order


@provider("coupon")
def _coupon(order):
    from coupons.models import CouponUse
    from coupons.service import coupon_discount

    use = CouponUse.objects.filter(order=order).select_related("coupon").first()
    return coupon_discount(use.coupon, order) if use else 0
