import uuid
from collections import defaultdict
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from core.errors import BusinessError
from core.services import get_setting
from notifications import events
from orders.lifecycle import cancel_by_company
from orders.models import Order
from orders.photos import shrink
from scheduling.availability import local_day_bounds
from scheduling.models import ClosedDay

from .models import DamagePhoto, DamageReport, Rating, RatingPhoto, RatingTag

MAX_PHOTOS = 6  # technical limit per rating / report


def _own_completed(order, customer):
    if order.customer_id != customer.id:
        raise BusinessError("not_your_order", "الطلب ده مش بتاعك.", status=403)
    if order.status != Order.Status.COMPLETED:
        raise BusinessError("not_completed", "ده متاح بعد ما الشغل يخلص.")


@transaction.atomic
def add_rating(order, customer, stars, tag_ids, comment="", call_requested=False):
    order = Order.objects.select_for_update().get(pk=order.pk)
    _own_completed(order, customer)
    if not isinstance(stars, int) or not 1 <= stars <= 5:
        raise BusinessError("bad_stars", "التقييم من 1 لـ 5 نجوم.")
    if Rating.objects.filter(order=order).exists():
        raise BusinessError("already_rated", "الطلب ده اتقيّم قبل كده.")
    r = Rating.objects.create(order=order, customer=customer, technician=order.technician, zone=order.zone,
                              stars=stars, comment=(comment or "")[:1000], call_requested=bool(call_requested))
    r.tags.set(RatingTag.objects.filter(pk__in=tag_ids or [], is_active=True))
    extra = {}
    if r.is_bad:
        events.bad_rating(r)
    elif stars == 5:
        # Polite prompt only; no reward for a Google review.
        extra["google_review_link"] = get_setting("google-maps-review-link")
    return r, extra


def add_rating_photo(rating, customer, data):
    if rating.customer_id != customer.id:
        raise BusinessError("not_your_order", "مش مسموح.", status=403)
    if rating.photos.count() >= MAX_PHOTOS:
        raise BusinessError("too_many_photos", "عدد الصور كفاية.")
    jpeg, _ = shrink(data)
    p = RatingPhoto(rating=rating)
    p.image.save(f"{rating.id}-{uuid.uuid4().hex}.jpg", ContentFile(jpeg), save=False)
    p.save()
    return p


@transaction.atomic
def handle_rating(rating, manager, note):
    if not (note or "").strip():
        raise BusinessError("note_required", "اكتب اتعمل إيه.")
    rating.handled_at = timezone.now()
    rating.handled_by = manager
    rating.handle_note = note.strip()[:500]
    rating.save()
    return rating


def ratings_summary():
    def avg(rows):
        return [{**r, "average": round(r["average"], 2)} for r in rows]

    by_tech = avg(Rating.objects.values("technician__id", "technician__full_name")
                  .annotate(average=Avg("stars"), count=Count("id")).order_by("technician__full_name"))
    by_zone = avg(Rating.objects.values("zone__name").annotate(average=Avg("stars"), count=Count("id"))
                  .order_by("zone__name"))
    per_service = defaultdict(list)
    for r in Rating.objects.prefetch_related("order__items"):
        names = {line["name"] for item in r.order.items.all() for line in item.quote["lines"]}
        for n in names:
            per_service[n].append(r.stars)
    by_service = [{"service": k, "average": round(sum(v) / len(v), 2), "count": len(v)}
                  for k, v in sorted(per_service.items())]
    return {
        "by_technician": [{"technician": r["technician__id"], "name": r["technician__full_name"],
                           "average": r["average"], "count": r["count"]} for r in by_tech],
        "by_zone": [{"zone": r["zone__name"], "average": r["average"], "count": r["count"]} for r in by_zone],
        "by_service": by_service,
    }


@transaction.atomic
def report_damage(order, customer, description):
    order = Order.objects.get(pk=order.pk)  # current status
    _own_completed(order, customer)
    if not (description or "").strip():
        raise BusinessError("description_required", "اكتب وصف الضرر.")
    window = timedelta(hours=get_setting("damage-report-within-hours"))
    finished = order.actual_end or order.scheduled_end
    if timezone.now() > finished + window:
        raise BusinessError("report_window_closed", "عدت المدة المسموحة للإبلاغ عن ضرر.")
    report = DamageReport.objects.create(order=order, customer=customer, description=description.strip()[:1000])
    events.damage_report(report)
    return report


def add_damage_photo(report, customer, data):
    if report.customer_id != customer.id:
        raise BusinessError("not_your_order", "مش مسموح.", status=403)
    if report.photos.count() >= MAX_PHOTOS:
        raise BusinessError("too_many_photos", "عدد الصور كفاية.")
    jpeg, _ = shrink(data)
    p = DamagePhoto(report=report)
    p.image.save(f"{report.id}-{uuid.uuid4().hex}.jpg", ContentFile(jpeg), save=False)
    p.save()
    return p


@transaction.atomic
def resolve_damage(report, manager, note):
    if not (note or "").strip():
        raise BusinessError("note_required", "اكتب اتعمل إيه.")
    report.status = DamageReport.Status.RESOLVED
    report.resolved_at = timezone.now()
    report.resolved_by = manager
    report.resolution_note = note.strip()[:1000]
    report.save()
    return report


@transaction.atomic
def close_day(day, zone, reason, manager):
    """Close a date (zone=None: all zones). Orders not started yet that day are
    cancelled by the company, free; the customer gets a 'book again' button.
    Returns how many orders were cancelled."""
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError("reason_required", "اكتب سبب القفل.")
    closed = ClosedDay.objects.create(date=day, zone=zone, reason=reason[:200], created_by=manager)
    start, end = local_day_bounds(day)
    qs = Order.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end,
                              status__in=[Order.Status.PENDING_PAYMENT, Order.Status.CONFIRMED])
    if zone is not None:
        qs = qs.filter(zone=zone)
    n = 0
    for order in qs:
        cancel_by_company(order, manager, reason)
        events.day_closed(order, reason)
        n += 1
    return n, closed
