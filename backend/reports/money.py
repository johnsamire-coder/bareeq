"""Manager reports for a period. All money is integer piastres.

- Revenue = what completed orders were worth (services after discounts and
  coupons, oil, older fees added) = their invoice total.
- Collected = real money in (cash collected + confirmed InstaPay).
- Wallet = paid from the wallet (gift balance).  Revenue - collected - wallet = still uncollected.
- Wash margin = services income - oil - materials (no technician pay or fuel).
"""
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsManager
from core.errors import BusinessError
from feedback.models import Rating
from orders.models import CustomerCharge, Order
from payments.models import Payment, WalletEntry
from scheduling.availability import CAIRO, local_day_bounds

S = Order.Status


def _period(request):
    p = request.query_params
    today = timezone.now().astimezone(CAIRO).date()
    try:
        start = date.fromisoformat(p["from"]) if p.get("from") else today.replace(day=1)
        end = date.fromisoformat(p["to"]) if p.get("to") else today
    except ValueError:
        raise BusinessError("bad_date", "التاريخ مش صحيح.")
    if end < start:
        raise BusinessError("bad_period", "تاريخ النهاية قبل البداية.")
    if (end - start).days > 400:
        raise BusinessError("bad_period", "الفترة طويلة قوي (أقصى حاجة 400 يوم).")
    return start, end


def build_report(start, end):
    t0, _ = local_day_bounds(start)
    _, t1 = local_day_bounds(end)
    done = list(Order.objects.filter(status=S.COMPLETED, scheduled_start__gte=t0, scheduled_start__lt=t1)
                .select_related("zone", "technician").prefetch_related("items", "payments"))

    def money_of(o):
        collected = sum(p.amount for p in o.payments.all() if p.status in (Payment.Status.COLLECTED, Payment.Status.CONFIRMED))
        oil = sum((i.quote.get("oil") or {}).get("price", 0) for i in o.items.all())
        return {"revenue": o.amount_due, "collected": collected, "wallet": o.wallet_used,
                "oil": oil, "materials": o.materials_cost, "margin": o.total - oil - o.materials_cost}

    totals = defaultdict(int)
    by_day, by_zone, by_tech = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    by_service = defaultdict(lambda: defaultdict(int))
    times = defaultdict(list)
    for o in done:
        m = money_of(o)
        for k, v in m.items():
            totals[k] += v
        day = o.scheduled_start.astimezone(CAIRO).date().isoformat()
        for bucket, key in ((by_day, day), (by_zone, o.zone.name), (by_tech, o.technician.full_name if o.technician else "-")):
            bucket[key]["orders"] += 1
            bucket[key]["revenue"] += m["revenue"]
            bucket[key]["margin"] += m["margin"]
        items = list(o.items.all())
        for it in items:
            for line in it.quote["lines"]:
                by_service[line["name"]]["count"] += 1
                by_service[line["name"]]["revenue"] += line["price"]
        # Real job time: only clean cases (one car, one service) so the time belongs to that service.
        if o.actual_start and o.actual_end and len(items) == 1 and len(items[0].quote["lines"]) == 1:
            line = items[0].quote["lines"][0]
            actual = round((o.actual_end - o.actual_start).total_seconds() / 60)
            times[(line["name"], items[0].size_class)].append((actual, line["minutes"]))
    totals["orders"] = len(done)
    totals["uncollected"] = totals["revenue"] - totals["collected"] - totals["wallet"]

    # New vs returning customers (among those with a completed order in the period).
    served = {o.customer_id for o in done}
    before = set(Order.objects.filter(customer__in=served, status=S.COMPLETED, scheduled_start__lt=t0)
                 .values_list("customer", flat=True))
    signups = User.objects.filter(role=User.Role.CUSTOMER, date_joined__gte=t0, date_joined__lt=t1).count()

    cancelled = dict(Order.objects.filter(scheduled_start__gte=t0, scheduled_start__lt=t1, status__in=[
        S.CANCELLED_BY_CUSTOMER, S.CANCELLED_BY_COMPANY, S.CAR_NOT_FOUND]).values("status")
        .annotate(n=Count("id")).values_list("status", "n"))

    ratings = Rating.objects.filter(created_at__gte=t0, created_at__lt=t1)
    now = timezone.now()

    def rows(d):
        return [{"name": k, **dict(v)} for k, v in sorted(d.items(), key=lambda kv: -kv[1]["revenue"])]

    return {
        "from": start.isoformat(), "to": end.isoformat(),
        "totals": dict(totals),
        "by_day": [{"date": k, **dict(v)} for k, v in sorted(by_day.items())],
        "by_zone": rows(by_zone),
        "by_technician": rows(by_tech),
        "by_service": rows(by_service),
        "customers": {"signups": signups, "served": len(served), "returning": len(served & before),
                      "first_time": len(served - before)},
        "job_times": [{"service": s, "size": z, "count": len(v), "actual_avg": round(sum(a for a, _ in v) / len(v)),
                       "planned": v[0][1]} for (s, z), v in sorted(times.items())],
        "cancellations": {"by_customer": cancelled.get(S.CANCELLED_BY_CUSTOMER, 0),
                          "by_company": cancelled.get(S.CANCELLED_BY_COMPANY, 0),
                          "car_not_found": cancelled.get(S.CAR_NOT_FOUND, 0)},
        "ratings": {"count": ratings.count(), "average": round(ratings.aggregate(a=Avg("stars"))["a"] or 0, 2)},
        # Snapshots (today, not the period):
        "now": {
            "wallet_liability": WalletEntry.objects.filter(kind__in=WalletEntry.CREDIT_KINDS, remaining__gt=0,
                                                           expires_at__gt=now).aggregate(s=Sum("remaining"))["s"] or 0,
            "unpaid_fees": CustomerCharge.objects.filter(waived_at__isnull=True, applied_to_order__isnull=True)
            .aggregate(s=Sum("amount"))["s"] or 0,
        },
    }


@api_view(["GET"])
@permission_classes([IsManager])
def report(request):
    start, end = _period(request)
    return Response(build_report(start, end))
