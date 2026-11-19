"""Registers the wash card and referral first-order discounts (orders/discounts.py)."""
from core.services import get_setting
from orders.discounts import provider


@provider("wash_card")
def _wash_card(order):
    from .wash_card import reward_for

    return reward_for(order)


@provider("referral")
def _referral(order):
    """Only on the invited customer's first order."""
    from orders.models import Order

    from .models import Referral

    if not get_setting("referral-enabled"):
        return 0
    if not Referral.objects.filter(referee=order.customer, status=Referral.Status.PENDING).exists():
        return 0
    others = (Order.Status.CONFIRMED, Order.Status.ON_THE_WAY, Order.Status.ARRIVED, Order.Status.IN_PROGRESS,
              Order.Status.COMPLETED)
    if Order.objects.filter(customer=order.customer, status__in=others).exclude(pk=order.pk).exists():
        return 0
    return get_setting("referral-new-customer-discount")
