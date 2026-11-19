from datetime import date

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsManager
from core.errors import BusinessError
from core.services import get_setting
from orders.models import Order
from payments import wallet
from payments.models import WalletEntry
from scheduling.availability import CAIRO

from . import referral as referral_service
from . import wash_card
from .models import Referral
from .refunds import refund_to_wallet
from .serializers import ReferralSerializer


@api_view(["GET"])
@permission_classes([IsCustomer])
def my_rewards(request):
    """Everything the customer's «مكافآتي» screen shows."""
    u = request.user
    mine = Referral.objects.filter(referrer=u)
    earned = WalletEntry.objects.filter(customer=u, kind=WalletEntry.Kind.REFERRAL).aggregate(s=Sum("amount"))["s"]
    cashback = WalletEntry.objects.filter(customer=u, kind=WalletEntry.Kind.CASHBACK).aggregate(s=Sum("amount"))["s"]
    return Response({
        "wallet_balance": wallet.balance(u),
        "cashback": {"enabled": bool(get_setting("cashback-enabled")), "percent": get_setting("cashback-percent"),
                     "earned": cashback or 0},
        "wash_card": wash_card.status(u),
        "referral": {
            "enabled": bool(get_setting("referral-enabled")),
            "code": referral_service.code_for(u),
            "new_customer_discount": get_setting("referral-new-customer-discount"),
            "referrer_credit": get_setting("referral-referrer-credit"),
            "invited": mine.count(),
            "credited": mine.filter(status=Referral.Status.CREDITED).count(),
            "earned": earned or 0,
        },
    })


@api_view(["POST"])
@permission_classes([IsCustomer])
def order_refund_to_wallet(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    option = refund_to_wallet(order, request.user)
    return Response({**option, "wallet_balance": wallet.balance(request.user)})


@api_view(["GET"])
@permission_classes([IsManager])
def manager_referrals(request):
    qs = Referral.objects.select_related("referee", "referrer")
    if s := request.query_params.get("status"):
        qs = qs.filter(status=s)
    return Response(ReferralSerializer(qs[:200], many=True).data)


@api_view(["POST"])
@permission_classes([IsManager])
def manager_referral_decide(request, pk, decision):
    r = get_object_or_404(Referral, pk=pk)
    if decision not in ("approve", "reject"):
        raise BusinessError("bad_decision", "اختار موافقة أو رفض.", status=404)
    if decision == "approve":
        r = referral_service.approve(r, request.user)
    else:
        r = referral_service.reject(r, request.user, request.data.get("reason", ""))
    return Response(ReferralSerializer(r).data)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_wallet_report(request):
    """Open wallet liability now, and what was credited / spent / expired in a month (SPEC 11)."""
    month = request.query_params.get("month")  # YYYY-MM, default this month
    today = timezone.now().astimezone(CAIRO).date()
    try:
        y, m = (int(x) for x in month.split("-")) if month else (today.year, today.month)
        first = date(y, m, 1)
    except (ValueError, AttributeError):
        raise BusinessError("bad_month", "الشهر مش صحيح (مثال: 2026-11).")
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    from scheduling.availability import local_day_bounds

    start, _ = local_day_bounds(first)
    end, _ = local_day_bounds(nxt)
    rows = WalletEntry.objects.filter(created_at__gte=start, created_at__lt=end)
    credited = {k: 0 for k in WalletEntry.CREDIT_KINDS}
    for r in rows.filter(kind__in=WalletEntry.CREDIT_KINDS).values("kind").annotate(s=Sum("amount")):
        credited[r["kind"]] = r["s"]
    labels = dict(WalletEntry.Kind.choices)
    now = timezone.now()
    return Response({
        "month": f"{y:04d}-{m:02d}",
        "liability_now": WalletEntry.objects.filter(kind__in=WalletEntry.CREDIT_KINDS, remaining__gt=0,
                                                    expires_at__gt=now).aggregate(s=Sum("remaining"))["s"] or 0,
        "credited": [{"kind": k, "label": labels[k], "amount": v} for k, v in credited.items()],
        "credited_total": sum(credited.values()),
        "spent": -(rows.filter(kind=WalletEntry.Kind.SPEND).aggregate(s=Sum("amount"))["s"] or 0),
        "expired": -(rows.filter(kind=WalletEntry.Kind.EXPIRY).aggregate(s=Sum("amount"))["s"] or 0),
    })
