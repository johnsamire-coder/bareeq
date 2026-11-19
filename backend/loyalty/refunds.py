"""A cancelled order that was paid by InstaPay (SPEC 11): the customer chooses
to get the money back, or to keep it in the wallet with a bonus %."""
from django.db import transaction

from core.errors import BusinessError
from core.services import get_setting


def wallet_option(order):
    """{"amount", "wallet_amount", "bonus"} when the customer can choose, else None.
    Only money the manager already confirmed (not a transfer still under review)."""
    from payments.models import Payment
    from payments.wallet import whole_pounds

    due = order.payments.filter(method__in=[Payment.Method.INSTAPAY, Payment.Method.CARD], status=Payment.Status.REFUND_DUE,
                                reviewed_at__isnull=False)
    amount = sum(p.amount for p in due)
    if amount <= 0:
        return None
    bonus = whole_pounds(amount * get_setting("refund-to-wallet-bonus-percent") // 100)
    return {"amount": amount, "bonus": bonus, "wallet_amount": amount + bonus}


@transaction.atomic
def refund_to_wallet(order, customer):
    from orders.models import Order
    from payments import wallet
    from payments.models import Payment, WalletEntry

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.customer_id != customer.id:
        raise BusinessError("not_your_order", "الطلب ده مش بتاعك.", status=403)
    payments = list(order.payments.select_for_update().filter(
        method__in=[Payment.Method.INSTAPAY, Payment.Method.CARD], status=Payment.Status.REFUND_DUE, reviewed_at__isnull=False))
    option = wallet_option(order)
    if not payments or option is None:
        raise BusinessError("nothing_to_refund", "مفيش فلوس مستنية ترجع في الطلب ده.")
    wallet.credit(customer, option["wallet_amount"], WalletEntry.Kind.REFUND, order=order,
                  note=f"فلوس طلب {order.id} في المحفظة (+{option['bonus'] // 100} جنيه زيادة)")
    for p in payments:
        p.status = Payment.Status.REFUNDED_TO_WALLET
        p.save(update_fields=["status"])
    return option
