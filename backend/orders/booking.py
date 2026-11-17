"""Booking: available slots, temporary hold, auto-assign, confirm, move a job."""
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from cars.models import CustomerCar
from core.errors import BusinessError
from core.services import get_setting
from places.models import Address
from scheduling.availability import (
    CAIRO,
    config,
    jobs_for,
    schedulable_technicians,
    shift_for,
    travel_function,
)
from scheduling.engine import can_fit, slot_grid
from scheduling.models import TechnicianProfile
from services.pricing import build_quote

from .charges import attach_to_order, charges_payload, outstanding_charges, release_from_order
from .models import CustomerCharge, Order, OrderItem


@dataclass
class Prepared:
    address: Address
    zone: object
    place: tuple
    lines: list = field(default_factory=list)  # (car, quote)

    @property
    def minutes(self):
        return sum(q["total_minutes"] for _, q in self.lines)

    @property
    def subtotal(self):
        return sum(q["subtotal"] + (q["oil"]["price"] if q["oil"] else 0) for _, q in self.lines)

    @property
    def discount(self):
        return sum(q["discount"] for _, q in self.lines)

    @property
    def total(self):
        return sum(q["total"] for _, q in self.lines)


def prepare(customer, address_id, items):
    if not items:
        raise BusinessError("no_cars", "اختار عربية واحدة على الأقل.")
    address = Address.objects.filter(pk=address_id, customer=customer, is_active=True).select_related("zone").first()
    if address is None:
        raise BusinessError("address_not_found", "العنوان مش موجود.")
    zone = address.zone
    if zone is None or not zone.is_active:
        raise BusinessError("outside_service_area", "العنوان ده برا المناطق اللي بنخدمها دلوقتي.")
    car_ids = [int(i["car"]) for i in items]
    if len(set(car_ids)) != len(car_ids):
        raise BusinessError("duplicate_car", "نفس العربية متكررة في الطلب.")
    cars = {c.id: c for c in CustomerCar.objects.filter(pk__in=car_ids, customer=customer, is_active=True)}
    if len(cars) != len(car_ids):
        raise BusinessError("car_not_found", "العربية مش موجودة.")
    prepared = Prepared(address=address, zone=zone, place=(address.lat, address.lng))
    for item in items:
        car = cars[int(item["car"])]
        q = build_quote(item.get("services") or [], zone, car.size_class, car.parking, item.get("oil_type"))
        prepared.lines.append((car, q))
    return prepared


def _window(now):
    """(earliest allowed start, list of bookable local dates)."""
    earliest = now + timedelta(minutes=get_setting("scheduling-min-notice-minutes"))
    today = now.astimezone(CAIRO).date()
    days = [today + timedelta(days=i) for i in range(get_setting("scheduling-days-ahead"))]
    return earliest, days


def available_slots(customer, address_id, items):
    prep = prepare(customer, address_id, items)
    now = timezone.now()
    earliest, days = _window(now)
    step = get_setting("scheduling-slot-step-minutes")
    cfg, travel = config(), travel_function()
    techs = schedulable_technicians(prep.zone)
    result_days = []
    for day in days:
        counts = {}
        for profile in techs:
            shift = shift_for(profile, day)
            if shift is None:
                continue
            jobs = jobs_for(profile.user, day)
            for t in slot_grid(max(shift[0], earliest), shift[1], step):
                if can_fit(t, prep.minutes, prep.place, jobs, shift, profile.home, cfg, travel):
                    counts[t] = counts.get(t, 0) + 1
        result_days.append({
            "date": day.isoformat(),
            "slots": [{"start": t, "free_technicians": counts[t]} for t in sorted(counts)],
        })
    charges = outstanding_charges(customer)
    charges_total = sum(c.amount for c in charges)
    return {
        "total_minutes": prep.minutes,
        "subtotal": prep.subtotal,
        "discount": prep.discount,
        "total": prep.total,
        # Older unpaid fees, shown BEFORE the customer confirms, added as their own line.
        "charges": charges_payload(charges),
        "charges_total": charges_total,
        "amount_due": prep.total + charges_total,
        "cars": [{"car": car.id, "quote": q} for car, q in prep.lines],
        "days": result_days,
    }


def _check_start(start, now):
    if timezone.is_naive(start):
        raise BusinessError("invalid_slot", "الميعاد مش صحيح.")
    earliest, days = _window(now)
    local = start.astimezone(CAIRO)
    step = get_setting("scheduling-slot-step-minutes")
    on_grid = local.second == 0 and local.microsecond == 0 and (local.hour * 60 + local.minute) % step == 0
    if not on_grid or start < earliest or local.date() not in days:
        raise BusinessError("invalid_slot", "الميعاد ده مش متاح. اختار ميعاد من القايمة.")


def _travel_from_previous(profile, jobs, t, place, travel):
    before = [j for j in jobs if j.start <= t]
    origin = max(before, key=lambda j: j.start).place if before else profile.home
    return travel(origin, place)


@transaction.atomic
def create_order(customer, address_id, items, start):
    prep = prepare(customer, address_id, items)
    now = timezone.now()
    _check_start(start, now)
    cfg, travel = config(), travel_function()
    day = start.astimezone(CAIRO).date()

    # Lock the zone's technicians so two customers cannot take the same time.
    best = None
    for profile in schedulable_technicians(prep.zone, lock=True):
        shift = shift_for(profile, day)
        jobs = jobs_for(profile.user, day)
        if can_fit(start, prep.minutes, prep.place, jobs, shift, profile.home, cfg, travel):
            # Nearest first; then the one with fewer jobs that day.
            key = (_travel_from_previous(profile, jobs, start, prep.place, travel), len(jobs), profile.user_id)
            if best is None or key < best[0]:
                best = (key, profile)
    if best is None:
        raise BusinessError("slot_taken", "الميعاد ده اتحجز. اختار ميعاد تاني.", status=409)

    order = Order.objects.create(
        customer=customer, address=prep.address, zone=prep.zone, lat=prep.address.lat, lng=prep.address.lng,
        technician=best[1].user, scheduled_start=start, scheduled_end=start + timedelta(minutes=prep.minutes),
        total_minutes=prep.minutes, status=Order.Status.PENDING_PAYMENT,
        hold_expires_at=now + timedelta(minutes=get_setting("scheduling-slot-hold-minutes")),
        subtotal=prep.subtotal, discount=prep.discount, total=prep.total,
    )
    for car, q in prep.lines:
        OrderItem.objects.create(order=order, car=car, size_class=car.size_class, quote=q,
                                 minutes=q["total_minutes"], total=q["total"])
    attach_to_order(order)
    return order


PAYMENT_METHODS_NOW = ("cash",)  # InstaPay and wallet arrive in step 9


@transaction.atomic
def confirm_order(order, payment_method):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if payment_method not in PAYMENT_METHODS_NOW:
        raise BusinessError("payment_method_not_available", "طريقة الدفع دي لسه مش متاحة.")
    if order.status != Order.Status.PENDING_PAYMENT:
        raise BusinessError("not_pending", "الطلب ده مش مستني تأكيد.")
    if order.hold_expires_at and order.hold_expires_at <= timezone.now():
        release_from_order(order)
        order.status = Order.Status.EXPIRED
        order.save(update_fields=["status", "updated_at"])
        raise BusinessError("hold_expired", "خلص وقت الحجز المؤقت. اختار الميعاد تاني.")
    order.status = Order.Status.CONFIRMED
    order.payment_method = payment_method
    order.hold_expires_at = None
    order.save(update_fields=["status", "payment_method", "hold_expires_at", "updated_at"])
    return order


@transaction.atomic
def expire_holds():
    expired = list(Order.objects.select_for_update().filter(
        status=Order.Status.PENDING_PAYMENT, hold_expires_at__lte=timezone.now()))
    for order in expired:
        release_from_order(order)
    return Order.objects.filter(pk__in=[o.pk for o in expired]).update(
        status=Order.Status.EXPIRED, updated_at=timezone.now())


MOVABLE = (Order.Status.PENDING_PAYMENT, Order.Status.CONFIRMED)


@transaction.atomic
def reassign(order, technician, force=False):
    """Manager moves a job to another technician. Checks that he covers the
    zone and has room, unless force=True. (The customer notification arrives
    with notifications in step 10.)"""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status not in MOVABLE:
        raise BusinessError("not_movable", "الطلب ده مينفعش يتنقل دلوقتي.")
    profile = TechnicianProfile.objects.select_for_update().filter(
        user=technician, user__role="technician", user__is_active=True
    ).first()
    if profile is None:
        raise BusinessError("technician_not_found", "الفني مش موجود.")
    if not force:
        day = order.scheduled_start.astimezone(CAIRO).date()
        ok = (
            profile.zones.filter(pk=order.zone_id).exists()
            and profile.home is not None
            and can_fit(order.scheduled_start, order.total_minutes, order.place,
                        jobs_for(technician, day, exclude_order_id=order.pk),
                        shift_for(profile, day), profile.home, config(), travel_function())
        )
        if not ok:
            raise BusinessError("technician_not_available", "الفني ده مش فاضي في الميعاد ده أو مش بيغطي المنطقة.")
    order.technician = technician
    order.save(update_fields=["technician", "updated_at"])
    return order
