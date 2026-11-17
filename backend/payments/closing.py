"""Materials per job and the technician's daily cash closing."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.errors import BusinessError
from orders.models import Order
from scheduling.availability import CAIRO, local_day_bounds

from .models import DailyClosing, Material, MaterialUsage, Payment, TechnicianCustody


def _day_of(order):
    return order.scheduled_start.astimezone(CAIRO).date()


def _closed(technician, day):
    return DailyClosing.objects.filter(technician=technician, date=day, status=DailyClosing.Status.CONFIRMED).exists()


@transaction.atomic
def record_materials(order, technician, items):
    """Replace the job's materials list. items: [{material, quantity}]."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.technician_id != technician.id:
        raise BusinessError("not_your_job", "الطلب ده مش بتاعك.", status=403)
    if order.status not in (Order.Status.IN_PROGRESS, Order.Status.COMPLETED):
        raise BusinessError("wrong_status", "الخامات بتتسجل وقت الشغل أو بعده.")
    if _closed(technician, _day_of(order)):
        raise BusinessError("day_closed", "اليوم ده اتقفل. كلم المدير.")
    rows = []
    for item in items:
        try:
            qty = Decimal(str(item["quantity"]))
        except (InvalidOperation, KeyError, TypeError):
            raise BusinessError("bad_quantity", "الكمية مش صحيحة.")
        if not qty.is_finite() or qty <= 0:
            raise BusinessError("bad_quantity", "الكمية لازم تبقى أكبر من صفر.")
        material = Material.objects.filter(pk=item.get("material"), is_active=True).first()
        if material is None:
            raise BusinessError("unknown_material", "الخامة مش موجودة.")
        cost = int((qty * material.unit_cost).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        rows.append(MaterialUsage(order=order, material=material, quantity=qty, unit_cost=material.unit_cost,
                                  cost=cost, recorded_by=technician))
    order.material_usages.all().delete()
    MaterialUsage.objects.bulk_create(rows)
    order.materials_cost = sum(r.cost for r in rows)
    order.save(update_fields=["materials_cost", "updated_at"])
    return order


def closing_summary(technician, day):
    start, end = local_day_bounds(day)
    orders = list(Order.objects.filter(technician=technician, status=Order.Status.COMPLETED,
                                       scheduled_start__gte=start, scheduled_start__lt=end)
                  .order_by("scheduled_start"))
    rows = []
    for o in orders:
        cash = o.payments.filter(method=Payment.Method.CASH, status=Payment.Status.COLLECTED
                                 ).aggregate(s=Sum("amount"))["s"] or 0
        rows.append({"order": o.id, "scheduled_start": o.scheduled_start, "amount_due": o.amount_due,
                     "revenue": o.revenue, "collected": o.collected, "wallet_used": o.wallet_used,
                     "uncollected": o.uncollected, "cash_collected": cash, "materials_cost": o.materials_cost,
                     "wash_margin": o.wash_margin})
    closing = DailyClosing.objects.filter(technician=technician, date=day).first()
    return {
        "date": day.isoformat(),
        "orders": rows,
        "cash_collected": sum(r["cash_collected"] for r in rows),
        # Revenue next to real money collected; the difference is the wallet part.
        "revenue": sum(r["revenue"] for r in rows),
        "collected": sum(r["collected"] for r in rows),
        "wallet_used": sum(r["wallet_used"] for r in rows),
        "uncollected": sum(r["uncollected"] for r in rows),
        "materials_cost": sum(r["materials_cost"] for r in rows),
        "wash_margin": sum(r["wash_margin"] for r in rows),
        "closing": None if closing is None else {
            "id": closing.id, "status": closing.status, "cash_handed": closing.cash_handed,
            "difference": closing.difference, "confirm_reason": closing.confirm_reason},
    }


@transaction.atomic
def submit_closing(technician, day, cash_handed, note=""):
    if not isinstance(cash_handed, int) or cash_handed < 0:
        raise BusinessError("bad_amount", "المبلغ مش صحيح.")
    existing = DailyClosing.objects.select_for_update().filter(technician=technician, date=day).first()
    if existing and existing.status == DailyClosing.Status.CONFIRMED:
        raise BusinessError("already_confirmed", "المدير استلم تقفيل اليوم ده خلاص.")
    expected = closing_summary(technician, day)["cash_collected"]
    closing, _ = DailyClosing.objects.update_or_create(
        technician=technician, date=day,
        defaults={"cash_expected": expected, "cash_handed": cash_handed, "difference": cash_handed - expected,
                  "note": (note or "")[:300], "submitted_at": timezone.now(),
                  "status": DailyClosing.Status.SUBMITTED},
    )
    return closing


@transaction.atomic
def confirm_closing(closing, manager, reason=""):
    """The manager receives the cash. Any difference needs a written reason and
    goes on the technician's custody: a shortage he owes, or an overage."""
    closing = DailyClosing.objects.select_for_update().get(pk=closing.pk)
    if closing.status != DailyClosing.Status.SUBMITTED:
        raise BusinessError("not_submitted", "التقفيل ده مش مستني تأكيد.")
    reason = (reason or "").strip()
    if closing.difference and not reason:
        raise BusinessError("reason_required", "فيه فرق في التقفيل. اكتب السبب الأول.")
    closing.status = DailyClosing.Status.CONFIRMED
    closing.confirmed_by = manager
    closing.confirmed_at = timezone.now()
    closing.confirm_reason = reason
    closing.save()
    if closing.difference:
        TechnicianCustody.objects.create(
            technician=closing.technician, closing=closing,
            kind=TechnicianCustody.Kind.SHORTAGE if closing.difference < 0 else TechnicianCustody.Kind.OVERAGE,
            amount=abs(closing.difference), note=reason, created_by=manager)
    return closing
