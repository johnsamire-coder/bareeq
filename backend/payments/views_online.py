"""Online payment endpoints: start, status, the company's callback, and the
test company's page (only while PAYMENT_GATEWAY=fake)."""
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import IsCustomer
from orders.models import Order

from . import online
from .gateway import get_gateway
from .models import OnlinePayment


def _status(p):
    return {"ref": p.ref, "order": p.order_id, "amount": p.amount, "wallet_amount": p.wallet_amount,
            "status": p.status, "status_label": p.get_status_display()}


@api_view(["POST"])
@permission_classes([IsCustomer])
def pay_online(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    p = online.start(order, request.user, request.data.get("wallet_amount") or 0)
    return Response({**_status(p), "redirect_url": get_gateway().checkout_url(p, request)}, status=201)


@api_view(["GET"])
@permission_classes([IsCustomer])
def payment_status(request, ref):
    return Response(_status(get_object_or_404(OnlinePayment, ref=ref, order__customer=request.user)))


@api_view(["POST"])
@permission_classes([AllowAny])
def callback(request, provider):
    if provider != settings.PAYMENT_GATEWAY:
        raise Http404
    p = online.handle_callback(provider, request.data)
    return Response({"ok": True, "status": p.status})


_PAGE = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>دفع تجريبي</title>
<style>body{{font-family:sans-serif;background:#F6FAFB;color:#0A2540;margin:0;padding:24px}}
.card{{background:#fff;border-radius:16px;padding:20px;max-width:420px;margin:auto;box-shadow:0 1px 4px #0001}}
.tag{{background:#FFC145;border-radius:8px;padding:6px 10px;font-weight:bold;display:inline-block}}
button{{width:100%;padding:14px;border:0;border-radius:12px;font-size:17px;margin-top:12px}}
.pay{{background:#12B5CB;color:#fff}} .no{{background:#E2E9EE}}</style></head><body><div class="card">
<span class="tag">صفحة دفع تجريبية: مفيش فلوس حقيقية</span>
{body}</div></body></html>"""


@csrf_exempt
def fake_page(request, ref):
    """What the real payment company's page will do, without real money."""
    if settings.PAYMENT_GATEWAY != "fake":
        raise Http404
    from .gateway.fake import sign

    p = get_object_or_404(OnlinePayment, ref=ref, provider="fake")
    if request.method == "POST" and p.status == OnlinePayment.Status.CREATED:
        paid = request.POST.get("action") == "pay"
        txn = f"FAKE-{p.id}"
        data = {"ref": p.ref, "paid": "1" if paid else "0", "amount": p.amount, "txn_id": txn,
                "signature": sign(p.ref, paid, p.amount, txn)}
        try:
            p = online.handle_callback("fake", data)
        except Exception as e:  # shown on the page, like a real company would
            return HttpResponse(_PAGE.format(body=f"<h2>حصلت مشكلة</h2><p>{escape(str(e))}</p>"))
    if p.status == OnlinePayment.Status.CREATED:
        body = (f"<h2>طلب {p.order_id}</h2><p>المبلغ: <b>{p.amount / 100:g} جنيه</b></p>"
                '<form method="post"><button class="pay" name="action" value="pay">ادفع</button>'
                '<button class="no" name="action" value="fail">ارفض (جرّب فشل الدفع)</button></form>')
    else:
        body = (f"<h2>{escape(p.get_status_display())}</h2>"
                "<p>ارجع للتطبيق، وهتلاقي حالة الطلب اتحدثت.</p>")
    return HttpResponse(_PAGE.format(body=body))
