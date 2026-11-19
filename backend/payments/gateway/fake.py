"""A test payment company: a simple page with «ادفع» and «ارفض» buttons and no
real money. It signs its answer exactly like a real company would, so the rest
of the system cannot tell the difference. Never used on the real server."""
import hashlib
import hmac

from django.conf import settings

from . import BadSignature, Result


def _key():
    # Derived from the server's own secret: no new secret to keep.
    return hmac.new(settings.SECRET_KEY.encode(), b"bareeq-fake-gateway", hashlib.sha256).digest()


def sign(ref, paid, amount, txn_id):
    msg = f"{ref}|{int(bool(paid))}|{amount}|{txn_id}".encode()
    return hmac.new(_key(), msg, hashlib.sha256).hexdigest()


class FakeGateway:
    name = "fake"

    def checkout_url(self, payment, request):
        return request.build_absolute_uri(f"/api/pay/fake/{payment.ref}/")

    def parse_callback(self, data):
        try:
            ref, paid, amount, txn = data["ref"], data["paid"] in (True, "1", 1, "true"), int(data["amount"]), \
                data.get("txn_id", "")
        except (KeyError, TypeError, ValueError):
            raise BadSignature("missing fields")
        if not hmac.compare_digest(sign(ref, paid, amount, txn), str(data.get("signature", ""))):
            raise BadSignature("bad signature")
        return Result(ref=ref, paid=paid, amount=amount, txn_id=txn)
