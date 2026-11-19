"""What happens after an order is done and paid: cashback, the friend's
referral credit, and the wash card messages. Safe to call more than once."""
from django.db import transaction

from core.services import get_setting


def is_paid(order):
    from orders.models import Order

    return order.status == Order.Status.COMPLETED and order.uncollected <= 0


def cashback_for(order):
    """X% of the real money paid for this order (cash + confirmed InstaPay, not
    the wallet, not older fees), rounded down to a whole pound."""
    from payments.wallet import whole_pounds

    base = max(0, order.collected - order.charges_total)
    return whole_pounds(base * get_setting("cashback-percent") // 100)


def give_cashback(order):
    from payments import wallet
    from payments.models import WalletEntry

    if not get_setting("cashback-enabled"):
        return None
    if WalletEntry.objects.filter(order=order, kind=WalletEntry.Kind.CASHBACK).exists():
        return None
    amount = cashback_for(order)
    if amount <= 0:
        return None
    return wallet.credit(order.customer, amount, WalletEntry.Kind.CASHBACK, order=order,
                         note=f"كاش باك طلب {order.id}")


@transaction.atomic
def on_completed(order):
    """Right after the technician finishes (and again when InstaPay is approved later)."""
    from .referral import after_paid_order
    from .wash_card import after_completed

    if order.status != "completed" or order.subscription_period_id:
        return  # subscription visits: no cashback, wash card or invite reward (agreed 19 Nov 2026)
    after_completed(order)
    if is_paid(order):
        give_cashback(order)
        after_paid_order(order)


def on_payment_confirmed(order):
    """InstaPay approved after the job was already done: now it is paid."""
    if order.status == "completed" and is_paid(order) and not order.subscription_period_id:
        from .referral import after_paid_order

        with transaction.atomic():
            give_cashback(order)
            after_paid_order(order)
