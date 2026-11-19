"""Live technician tracking (phase 4, agreed 19 Nov 2026): the technician's app
sends his position only while a job of his is «في الطريق»; the customer of that
job sees him on the map with a rough arrival time; the manager and supervisors
see everyone on the day's map. Positions are deleted after a few days."""
from datetime import timedelta

from django.utils import timezone

from core.errors import BusinessError
from core.services import get_setting
from scheduling.availability import travel_function

from .models import Order, TechnicianLocation


def active_job(technician):
    return Order.objects.filter(technician=technician, status=Order.Status.ON_THE_WAY).order_by(
        "scheduled_start").first()


def report(technician, lat, lng, accuracy=None):
    """Returns {"active": bool, "interval_seconds"}; stores the point only while on the way."""
    job = active_job(technician)
    out = {"active": job is not None, "interval_seconds": get_setting("tracking-interval-seconds")}
    if job is None or lat is None or lng is None:
        return out
    try:
        lat, lng = round(float(lat), 6), round(float(lng), 6)
    except (TypeError, ValueError):
        raise BusinessError("bad_location", "المكان مش صحيح.")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise BusinessError("bad_location", "المكان مش صحيح.")
    TechnicianLocation.objects.create(technician=technician, order=job, lat=lat, lng=lng,
                                      accuracy_m=int(accuracy) if accuracy else None, recorded_at=timezone.now())
    return out


def last_point(technician, fresh_minutes=None):
    qs = TechnicianLocation.objects.filter(technician=technician)
    if fresh_minutes:
        qs = qs.filter(recorded_at__gte=timezone.now() - timedelta(minutes=fresh_minutes))
    return qs.first()


def for_customer(order):
    """What the customer's order screen shows while the technician is coming."""
    if order.status != Order.Status.ON_THE_WAY or order.technician_id is None:
        return {"active": False}
    p = last_point(order.technician, get_setting("tracking-fresh-minutes"))
    if p is None:
        return {"active": True, "technician_name": order.technician.full_name, "lat": None, "lng": None}
    minutes = travel_function()((p.lat, p.lng), (order.lat, order.lng))
    return {"active": True, "technician_name": order.technician.full_name, "lat": float(p.lat),
            "lng": float(p.lng), "updated_at": p.recorded_at, "eta_minutes": minutes,
            "interval_seconds": get_setting("tracking-interval-seconds")}


def delete_old():
    cutoff = timezone.now() - timedelta(days=get_setting("tracking-keep-days"))
    n, _ = TechnicianLocation.objects.filter(recorded_at__lt=cutoff).delete()
    return n
