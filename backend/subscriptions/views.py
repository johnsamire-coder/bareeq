from datetime import date

from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsManager
from cars.models import CustomerCar
from core.errors import BusinessError
from core.services import get_setting
from payments.gateway import get_gateway
from places.models import Address
from scheduling.availability import CAIRO

from . import service
from .models import Subscription, SubscriptionPeriod, SubscriptionPlan
from .serializers import PeriodSerializer, PlanSerializer, SubscriptionSerializer


def _start(value):
    dt = parse_datetime(str(value or ""))
    if dt is None or timezone.is_naive(dt):
        raise BusinessError("invalid_slot", "الميعاد مش صحيح.")
    return dt


@api_view(["GET"])
@permission_classes([IsCustomer])
def plans(request):
    """Plans with the price for this car and address: ?car=&address="""
    if not get_setting("subscriptions-enabled"):
        return Response([])
    car = get_object_or_404(CustomerCar, pk=request.query_params.get("car"), customer=request.user, is_active=True)
    address = get_object_or_404(Address, pk=request.query_params.get("address"), customer=request.user,
                                is_active=True)
    out = []
    for p in SubscriptionPlan.objects.filter(is_active=True).prefetch_related("services"):
        price, normal = service.plan_price(p, car, address)
        out.append({"id": p.id, "name": p.name, "washes_per_month": p.washes_per_month,
                    "discount_percent": p.discount_percent, "services": [s.name for s in p.services.all()],
                    "service_ids": [s.id for s in p.services.all()], "price": price, "normal_price": normal,
                    "every_days": service.interval_days(p)})
    return Response(out)


@api_view(["GET", "POST"])
@permission_classes([IsCustomer])
def my_subscriptions(request):
    if request.method == "GET":
        qs = Subscription.objects.filter(customer=request.user).exclude(
            status=Subscription.Status.ENDED, periods__status="expired").distinct()
        return Response(SubscriptionSerializer(qs, many=True).data)
    if not get_setting("subscriptions-enabled"):
        raise BusinessError("subscriptions_off", "الاشتراك مش متاح دلوقتي.")
    d = request.data
    sub = service.subscribe(request.user, d.get("plan"), d.get("car"), d.get("address"), _start(d.get("start")))
    return Response(SubscriptionSerializer(sub).data, status=201)


def _mine(request, pk):
    return get_object_or_404(Subscription, pk=pk, customer=request.user)


@api_view(["POST"])
@permission_classes([IsCustomer])
def renew(request, pk):
    service.renew(_mine(request, pk), request.user)
    return Response(SubscriptionSerializer(_mine(request, pk)).data)


@api_view(["POST"])
@permission_classes([IsCustomer])
def stop_renewal(request, pk):
    return Response(SubscriptionSerializer(service.stop_renewal(_mine(request, pk), request.user)).data)


def _period(request, pk):
    return get_object_or_404(SubscriptionPeriod, pk=pk, subscription__customer=request.user)


@api_view(["POST"])
@permission_classes([IsCustomer])
def period_pay_online(request, pk):
    p = service.start_online(_period(request, pk), request.user, request.data.get("wallet_amount") or 0)
    return Response({"ref": p.ref, "amount": p.amount, "wallet_amount": p.wallet_amount, "status": p.status,
                     "redirect_url": get_gateway().checkout_url(p, request)}, status=201)


@api_view(["POST"])
@permission_classes([IsCustomer])
def period_pay_instapay(request, pk):
    period = service.pay_instapay(_period(request, pk), request.user, request.FILES.get("proof"),
                                  request.data.get("wallet_amount") or 0)
    return Response(PeriodSerializer(period).data)


@api_view(["POST"])
@permission_classes([IsCustomer])
def period_makeup(request, pk):
    order = service.book_makeup(_period(request, pk), request.user, _start(request.data.get("start")))
    from orders.serializers import OrderSerializer

    return Response(OrderSerializer(order).data, status=201)


class ManagerPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManager]
    serializer_class = PlanSerializer
    queryset = SubscriptionPlan.objects.prefetch_related("services")
    http_method_names = ["get", "post", "patch", "head", "options"]  # stop a plan instead of deleting it


@api_view(["GET"])
@permission_classes([IsManager])
def manager_subscriptions(request):
    qs = Subscription.objects.select_related("customer", "plan", "car", "technician")
    if s := request.query_params.get("status"):
        qs = qs.filter(status=s)
    return Response(SubscriptionSerializer(qs[:300], many=True).data)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_report(request):
    """Subscribers now, and the months paid in a calendar month (by payment date)."""
    month = request.query_params.get("month")
    today = timezone.now().astimezone(CAIRO).date()
    try:
        y, m = (int(x) for x in month.split("-")) if month else (today.year, today.month)
        first = date(y, m, 1)
    except (ValueError, AttributeError):
        raise BusinessError("bad_month", "الشهر مش صحيح (مثال: 2026-11).")
    from scheduling.availability import local_day_bounds

    start, _ = local_day_bounds(first)
    end, _ = local_day_bounds(date(y + (m == 12), m % 12 + 1, 1))
    paid = SubscriptionPeriod.objects.filter(status="paid", paid_at__gte=start, paid_at__lt=end)
    t = paid.aggregate(n=Count("id"), revenue=Sum("price"), normal=Sum("normal_price"), wallet=Sum("wallet_used"))
    return Response({
        "month": f"{y:04d}-{m:02d}",
        "active_subscriptions": Subscription.objects.filter(status="active", periods__status="paid").distinct().count(),
        "renewals_off": Subscription.objects.filter(status="active", renew=False).count(),
        "months_paid": t["n"] or 0, "new": paid.filter(number=1).count(), "renewed": paid.filter(number__gt=1).count(),
        "revenue": t["revenue"] or 0, "discount_given": (t["normal"] or 0) - (t["revenue"] or 0),
        "from_wallet": t["wallet"] or 0,
    })
