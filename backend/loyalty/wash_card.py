"""Wash card (SPEC 11): every N completed orders, the next order gets X% off
its services. An order counts once even with several cars (agreed 19 Nov 2026)."""
from core.services import get_setting


def progress(customer):
    """How many completed orders since the last order that used the reward."""
    from orders.models import Order

    done = Order.objects.filter(customer=customer, status=Order.Status.COMPLETED)
    last_reward = done.filter(extra_discount_kind="wash_card").order_by("-actual_end").first()
    if last_reward is not None:
        done = done.filter(actual_end__gt=last_reward.actual_end)
    return done.count()


def status(customer):
    n = get_setting("wash-card-every-n")
    count = progress(customer)
    return {"enabled": bool(get_setting("wash-card-enabled")), "every_n": n,
            "reward_percent": get_setting("wash-card-reward-percent"),
            "done": min(count, n), "next_is_reward": count >= n}


def reward_for(order):
    """Piastres off this order from the wash card (0 when not due)."""
    from orders.models import Order
    from orders.discounts import services_base

    if not get_setting("wash-card-enabled") or progress(order.customer) < get_setting("wash-card-every-n"):
        return 0
    # Only one booked order can hold the reward at a time.
    active = (Order.Status.CONFIRMED, Order.Status.ON_THE_WAY, Order.Status.ARRIVED, Order.Status.IN_PROGRESS)
    if Order.objects.filter(customer=order.customer, status__in=active, extra_discount_kind="wash_card"
                            ).exclude(pk=order.pk).exists():
        return 0
    return services_base(order) * get_setting("wash-card-reward-percent") // 100


def after_completed(order):
    """Tell the customer when the reward is close or ready."""
    from notifications import events

    s = status(order.customer)
    if not s["enabled"] or order.extra_discount_kind == "wash_card":
        return
    if s["next_is_reward"]:
        events.wash_card_ready(order.customer, s["reward_percent"], order)
    elif s["done"] == s["every_n"] - 1:
        events.wash_card_one_left(order.customer, s["reward_percent"], order)
