"""Detailed reports (phase 4): per technician, per zone, customers coming back
or lost, and an Excel file of any report to send on WhatsApp."""
import io
from collections import defaultdict
from datetime import timedelta

from django.core import signing
from django.db.models import Avg, Max
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsManager
from core.errors import BusinessError
from core.services import get_setting
from feedback.models import Rating
from orders.models import Order
from scheduling.availability import local_day_bounds

from .money import _period, build_report

S = Order.Status


def technicians_report(start, end):
    from payments.custody import custody_balance

    t0, _ = local_day_bounds(start)
    _, t1 = local_day_bounds(end)
    grace = timedelta(minutes=get_setting("reports-on-time-grace-minutes"))
    orders = Order.objects.filter(scheduled_start__gte=t0, scheduled_start__lt=t1, technician__isnull=False)
    rows = []
    for tech in User.objects.filter(role=User.Role.TECHNICIAN).order_by("full_name"):
        mine = [o for o in orders if o.technician_id == tech.id]
        done = [o for o in mine if o.status == S.COMPLETED]
        started = [o for o in done if o.actual_start]
        on_time = sum(1 for o in started if o.actual_start <= o.scheduled_start + grace)
        timed = [o for o in done if o.actual_start and o.actual_end]
        actual = sum((o.actual_end - o.actual_start).total_seconds() / 60 for o in timed)
        planned = sum(o.total_minutes for o in timed)
        ratings = Rating.objects.filter(technician=tech, created_at__gte=t0, created_at__lt=t1)
        bad = ratings.filter(stars__lte=get_setting("ratings-bad-max-stars")).count()
        rows.append({
            "technician": tech.id, "name": tech.full_name, "is_active": tech.is_active,
            "completed": len(done),
            "car_not_found": sum(1 for o in mine if o.status == S.CAR_NOT_FOUND),
            "cancelled_by_company": sum(1 for o in mine if o.status == S.CANCELLED_BY_COMPANY),
            "express": sum(1 for o in done if o.is_express),
            "on_time_percent": round(100 * on_time / len(started)) if started else None,
            "avg_actual_minutes": round(actual / len(timed)) if timed else None,
            "avg_planned_minutes": round(planned / len(timed)) if timed else None,
            "rating_avg": round(ratings.aggregate(a=Avg("stars"))["a"] or 0, 2), "ratings": ratings.count(),
            "bad_ratings": bad,
            "revenue": sum(o.amount_due for o in done),
            "materials_cost": sum(o.materials_cost for o in done),
            "custody_balance": custody_balance(tech),
        })
    rows.sort(key=lambda r: -r["revenue"])
    return {"from": start.isoformat(), "to": end.isoformat(), "rows": rows}


def zones_report(start, end):
    t0, _ = local_day_bounds(start)
    _, t1 = local_day_bounds(end)
    done = Order.objects.filter(status=S.COMPLETED, scheduled_start__gte=t0, scheduled_start__lt=t1).select_related(
        "zone")
    first_ever = {}
    for cid, oid in Order.objects.filter(status=S.COMPLETED).order_by("scheduled_start").values_list("customer", "id"):
        first_ever.setdefault(cid, oid)
    z = defaultdict(lambda: defaultdict(int))
    for o in done:
        r = z[o.zone.name]
        r["orders"] += 1
        r["revenue"] += o.amount_due
        r["distance_fees"] += o.distance_fee
        r["express"] += int(o.is_express)
        r["new_customers"] += int(first_ever.get(o.customer_id) == o.id)
    for name, r in z.items():
        r["rating_avg"] = round(Rating.objects.filter(zone__name=name, created_at__gte=t0, created_at__lt=t1)
                                .aggregate(a=Avg("stars"))["a"] or 0, 2)
    rows = [{"name": k, **dict(v)} for k, v in sorted(z.items(), key=lambda kv: -kv[1]["revenue"])]
    return {"from": start.isoformat(), "to": end.isoformat(), "rows": rows}


def retention_report(start, end):
    """Customers in the period, and who stopped coming (no completed order for
    the «وحشتنا» days as of the period's end)."""
    t0, _ = local_day_bounds(start)
    _, t1 = local_day_bounds(end)
    lost_after = timedelta(days=get_setting("winback-after-days"))
    last = dict(Order.objects.filter(status=S.COMPLETED, scheduled_start__lt=t1).values("customer").annotate(
        last=Max("scheduled_start")).values_list("customer", "last"))
    counts = defaultdict(int)
    for cid, when in Order.objects.filter(status=S.COMPLETED, scheduled_start__lt=t1).values_list("customer",
                                                                                                    "scheduled_start"):
        counts[cid] += 1
    served = set(Order.objects.filter(status=S.COMPLETED, scheduled_start__gte=t0, scheduled_start__lt=t1)
                 .values_list("customer", flat=True))
    lost = [cid for cid, when in last.items() if when < t1 - lost_after]
    from subscriptions.models import Subscription

    lost_rows = []
    for u in User.objects.filter(id__in=lost).order_by("full_name")[:200]:
        lost_rows.append({"customer": u.id, "name": u.full_name, "phone": u.phone, "orders": counts[u.id],
                          "last_order": last[u.id]})
    lost_rows.sort(key=lambda r: r["last_order"], reverse=True)
    return {
        "from": start.isoformat(), "to": end.isoformat(),
        "served": len(served), "first_time": sum(1 for c in served if counts[c] == 1),
        "returning": sum(1 for c in served if counts[c] > 1),
        "customers_ever": len(last), "came_twice_or_more": sum(1 for c in last if counts[c] > 1),
        "lost": len(lost), "lost_after_days": lost_after.days,
        "active_subscriptions": Subscription.objects.filter(status="active", periods__status="paid").distinct().count(),
        "lost_customers": lost_rows,
    }


@api_view(["GET"])
@permission_classes([IsManager])
def technicians(request):
    return Response(technicians_report(*_period(request)))


@api_view(["GET"])
@permission_classes([IsManager])
def zones(request):
    return Response(zones_report(*_period(request)))


@api_view(["GET"])
@permission_classes([IsManager])
def retention(request):
    return Response(retention_report(*_period(request)))


# ---------- Excel ----------

def _pounds(v):
    return round(v / 100, 2) if isinstance(v, int) else v


def sheets_for(kind, start, end):
    """[(sheet title, [header...], [[cell...]...])]"""
    if kind == "summary":
        r = build_report(start, end)
        t = r["totals"]
        return [
            ("الملخص", ["البند", "القيمة"], [
                ["عدد الطلبات", t.get("orders", 0)], ["الإيراد (ج.م)", _pounds(t.get("revenue", 0))],
                ["اتحصّل فعلاً (ج.م)", _pounds(t.get("collected", 0))], ["من المحفظة (ج.م)", _pounds(t.get("wallet", 0))],
                ["لسه متحصّلش (ج.م)", _pounds(t.get("uncollected", 0))], ["هامش الغسلة (ج.م)", _pounds(t.get("margin", 0))],
                ["متوسط التقييم", r["ratings"]["average"]]]),
            ("كل يوم", ["اليوم", "الطلبات", "الإيراد", "هامش الغسلة"],
             [[d["date"], d["orders"], _pounds(d["revenue"]), _pounds(d["margin"])] for d in r["by_day"]]),
            ("الخدمات", ["الخدمة", "العدد", "الإيراد"],
             [[s["name"], s["count"], _pounds(s["revenue"])] for s in r["by_service"]]),
        ]
    if kind == "technicians":
        rows = technicians_report(start, end)["rows"]
        return [("الفنيين", ["الفني", "طلبات خلصت", "في ميعاده %", "متوسط الوقت الفعلي (دقيقة)",
                             "متوسط الوقت المتوقع", "التقييم", "تقييمات وحشة", "العربية مش موجودة", "طلبات سريعة",
                             "الإيراد", "الخامات", "العهدة"],
                 [[x["name"], x["completed"], x["on_time_percent"], x["avg_actual_minutes"], x["avg_planned_minutes"],
                   x["rating_avg"], x["bad_ratings"], x["car_not_found"], x["express"], _pounds(x["revenue"]),
                   _pounds(x["materials_cost"]), _pounds(x["custody_balance"])] for x in rows])]
    if kind == "zones":
        rows = zones_report(start, end)["rows"]
        return [("المناطق", ["المنطقة", "الطلبات", "الإيراد", "عملاء جداد", "طلبات سريعة", "رسوم المسافة", "التقييم"],
                 [[x["name"], x["orders"], _pounds(x["revenue"]), x["new_customers"], x["express"],
                   _pounds(x["distance_fees"]), x["rating_avg"]] for x in rows])]
    if kind == "retention":
        r = retention_report(start, end)
        return [
            ("العملاء", ["البند", "العدد"], [
                ["اتخدموا في الفترة", r["served"]], ["أول مرة", r["first_time"]], ["رجعوا تاني", r["returning"]],
                ["كل العملاء اللي طلبوا", r["customers_ever"]], ["طلبوا مرتين أو أكتر", r["came_twice_or_more"]],
                [f"بطّلوا (مفيش طلب من {r['lost_after_days']} يوم)", r["lost"]],
                ["مشتركين دلوقتي", r["active_subscriptions"]]]),
            ("اللي بطّلوا", ["الاسم", "الموبايل", "عدد الطلبات", "آخر طلب"],
             [[x["name"], x["phone"], x["orders"], x["last_order"].strftime("%Y-%m-%d")] for x in r["lost_customers"]]),
        ]
    raise BusinessError("bad_report", "التقرير ده مش موجود.")


def build_xlsx(sheets):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    wb.remove(wb.active)
    for title, header, rows in sheets:
        ws = wb.create_sheet(title[:31])
        ws.sheet_view.rightToLeft = True
        ws.append(header)
        for c in ws[1]:
            c.font = Font(bold=True)
        for row in rows:
            ws.append(row)
        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col) + 2
            ws.column_dimensions[col[0].column_letter].width = min(max(width, 10), 40)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_SALT = "bareeq-report-download"


@api_view(["POST"])
@permission_classes([IsManager])
def export(request):
    """A short-lived link to the Excel file (the phone's browser downloads it)."""
    kind = request.data.get("report") or "summary"
    start, end = _period(type("R", (), {"query_params": request.data})())
    sheets_for(kind, start, end)  # check it builds
    token = signing.dumps({"k": kind, "f": start.isoformat(), "t": end.isoformat(), "u": request.user.id}, salt=_SALT)
    return Response({"url": request.build_absolute_uri(f"/api/reports/download/{token}/")})


@api_view(["GET"])
@permission_classes([AllowAny])
def download(request, token):
    try:
        d = signing.loads(token, salt=_SALT, max_age=600)
    except signing.BadSignature:
        raise BusinessError("link_expired", "اللينك ده انتهى. اطلع التقرير تاني.", status=403)
    if not User.objects.filter(pk=d["u"], role=User.Role.MANAGER, is_active=True).exists():
        raise BusinessError("forbidden", "مش مسموح.", status=403)
    from datetime import date

    data = build_xlsx(sheets_for(d["k"], date.fromisoformat(d["f"]), date.fromisoformat(d["t"])))
    resp = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="bareeq-{d["k"]}-{d["f"]}-{d["t"]}.xlsx"'
    return resp
