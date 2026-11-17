"""Order statuses after booking (SPEC section 7)."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.errors import BusinessError
from core.services import get_setting
from scheduling.availability import CAIRO, config, jobs_for, schedulable_technicians, shift_for, travel_function
from scheduling.engine import can_fit

from .charges import add_charge, release_from_order
from .models import CustomerCharge, Order, OrderEvent
from .photos import has_all_sides

S = Order.Status


def _lock(order):
    return Order.objects.select_for_update().get(pk=order.pk)


def _move(order, to_status, by, lat=None, lng=None, note="", **fields):
    OrderEvent.objects.create(order=order, from_status=order.status, to_status=to_status, by=by,
                              at=timezone.now(), lat=lat, lng=lng, note=note)
    order.status = to_status
    for k, v in fields.items():
        setattr(order, k, v)
    order.save()
    return order


def _technician_step(order, technician, allowed_from):
    order = _lock(order)
    if order.technician_id != technician.id:
        raise BusinessError("not_your_job", "الطلب ده مش بتاعك.", status=403)
    if order.status not in allowed_from:
        raise BusinessError("wrong_status", "الخطوة دي مش متاحة دلوقتي.")
    return order


@transaction.atomic
def on_the_way(order, technician, lat=None, lng=None):
    order = _technician_step(order, technician, [S.CONFIRMED])
    return _move(order, S.ON_THE_WAY, technician, lat, lng)


@transaction.atomic
def arrived(order, technician, lat=None, lng=None):
    order = _technician_step(order, technician, [S.ON_THE_WAY])
    return _move(order, S.ARRIVED, technician, lat, lng)


@transaction.atomic
def start_job(order, technician, lat=None, lng=None):
    order = _technician_step(order, technician, [S.ARRIVED])
    if not has_all_sides(order, "before"):
        raise BusinessError("before_photos_missing", "صوّر العربية من الأربع نواحي قبل ما تبدأ.")
    return _move(order, S.IN_PROGRESS, technician, lat, lng, actual_start=timezone.now())


@transaction.atomic
def complete_job(order, technician, lat=None, lng=None):
    order = _technician_step(order, technician, [S.IN_PROGRESS])
    if not has_all_sides(order, "after"):
        raise BusinessError("after_photos_missing", "صوّر العربية من الأربع نواحي بعد ما تخلص.")
    return _move(order, S.COMPLETED, technician, lat, lng, actual_end=timezone.now())


@transaction.atomic
def called_customer(order, technician):
    order = _technician_step(order, technician, [S.ARRIVED])
    order.called_customer_at = timezone.now()
    order.save(update_fields=["called_customer_at", "updated_at"])
    OrderEvent.objects.create(order=order, from_status=order.status, to_status=order.status, by=technician,
                              note="الفني اتصل بالعميل")
    return order


@transaction.atomic
def car_not_found(order, technician, lat, lng):
    order = _technician_step(order, technician, [S.ARRIVED])
    if lat is None or lng is None:
        raise BusinessError("location_required", "لازم مكانك الحالي.")
    if order.called_customer_at is None:
        raise BusinessError("call_customer_first", "اتصل بالعميل الأول.")
    wait = timedelta(minutes=get_setting("car-not-found-wait-minutes"))
    if timezone.now() < order.called_customer_at + wait:
        raise BusinessError("wait_more", "لازم تستنى العميل المدة المحددة بعد ما تتصل بيه.")
    release_from_order(order)
    _move(order, S.CAR_NOT_FOUND, technician, lat, lng)
    add_charge(order.customer, CustomerCharge.Kind.CAR_NOT_FOUND, get_setting("car-not-found-fee"), order)
    return order


def _is_late(order):
    free_until = order.scheduled_start - timedelta(hours=get_setting("cancellation-free-until-hours"))
    return timezone.now() > free_until


@transaction.atomic
def cancel_by_customer(order, reason=""):
    order = _lock(order)
    if order.status not in (S.PENDING_PAYMENT, S.CONFIRMED):
        raise BusinessError("cannot_cancel", "الطلب ده مينفعش يتلغي دلوقتي. كلم خدمة العملاء.")
    late = order.status == S.CONFIRMED and _is_late(order)
    release_from_order(order)
    _move(order, S.CANCELLED_BY_CUSTOMER, order.customer, note=reason[:300], cancel_reason=reason[:300])
    if late:
        add_charge(order.customer, CustomerCharge.Kind.LATE_CANCELLATION, get_setting("cancellation-late-fee"), order)
    return order


@transaction.atomic
def cancel_by_company(order, manager, reason):
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError("reason_required", "لازم تكتب سبب الإلغاء.")
    order = _lock(order)
    if order.status not in (S.PENDING_PAYMENT, S.CONFIRMED, S.ON_THE_WAY, S.ARRIVED):
        raise BusinessError("cannot_cancel", "الطلب ده مينفعش يتلغي دلوقتي.")
    release_from_order(order)
    return _move(order, S.CANCELLED_BY_COMPANY, manager, note=reason[:300], cancel_reason=reason[:300])


@transaction.atomic
def reschedule(order, new_start):
    """Customer moves a confirmed order to another time (same price).
    Late (inside the free window) costs the late fee, like a cancellation."""
    from .booking import _check_start

    order = _lock(order)
    if order.status != S.CONFIRMED:
        raise BusinessError("cannot_reschedule", "الطلب ده مينفعش يتأجل دلوقتي.")
    _check_start(new_start, timezone.now())
    late = _is_late(order)
    day = new_start.astimezone(CAIRO).date()
    cfg, travel = config(), travel_function()
    fits = []
    for profile in schedulable_technicians(order.zone, lock=True):
        jobs = jobs_for(profile.user, day, exclude_order_id=order.pk)
        if can_fit(new_start, order.total_minutes, order.place, jobs, shift_for(profile, day), profile.home, cfg,
                   travel):
            fits.append(profile.user)
    if not fits:
        raise BusinessError("slot_taken", "الميعاد ده مش متاح. اختار ميعاد تاني.", status=409)
    # Keep the same technician when he can make it.
    tech = order.technician if order.technician in fits else fits[0]
    old = order.scheduled_start
    order.technician = tech
    order.scheduled_start = new_start
    order.scheduled_end = new_start + timedelta(minutes=order.total_minutes)
    order.save()
    OrderEvent.objects.create(order=order, from_status=order.status, to_status=order.status, by=order.customer,
                              note=f"اتأجل من {old.astimezone(CAIRO):%Y-%m-%d %H:%M}")
    if late:
        add_charge(order.customer, CustomerCharge.Kind.LATE_RESCHEDULE, get_setting("cancellation-late-fee"), order)
    return order
