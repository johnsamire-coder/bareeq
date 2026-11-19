"""Payment companies. Each one turns an OnlinePayment into a page where the
customer pays, and checks the signed message the company sends back.

To add the real company (Paymob, step 2), write a class with the same methods
and add it to GATEWAYS. Which one is used comes from PAYMENT_GATEWAY in .env."""
from dataclasses import dataclass

from django.conf import settings


@dataclass
class Result:
    ref: str            # our OnlinePayment.ref
    paid: bool          # the company says the money was taken
    amount: int         # piastres the company says it took
    txn_id: str = ""    # the company's own number for the payment


class BadSignature(Exception):
    """The message did not come from the payment company."""


def get_gateway(name=None):
    from .fake import FakeGateway

    gateways = {"fake": FakeGateway}
    return gateways[name or settings.PAYMENT_GATEWAY]()
