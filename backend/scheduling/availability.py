"""Glue between the database and the pure rules in engine.py."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings

from core.services import get_setting

from .engine import Config, Job
from .models import TechnicianProfile
from .travel import get_travel_estimator

CAIRO = ZoneInfo(settings.TIME_ZONE)


def local_day_bounds(day):
    return datetime.combine(day, time(0), tzinfo=CAIRO), datetime.combine(day + timedelta(days=1), time(0), tzinfo=CAIRO)


def config():
    return Config(get_setting("scheduling-buffer-minutes"), get_setting("scheduling-min-gap-minutes"))


def travel_function():
    estimator = get_travel_estimator()
    return estimator.minutes


def schedulable_technicians(zone, lock=False):
    """Active technicians covering the zone, with a start point set."""
    qs = TechnicianProfile.objects.filter(
        zones=zone, user__is_active=True, user__role="technician", start_lat__isnull=False, start_lng__isnull=False
    ).select_related("user").order_by("pk")
    if lock:
        qs = qs.select_for_update(of=("self",))
    return list(qs)


def shift_for(profile, day):
    """(start, end) as Cairo times, or None on a day off."""
    if profile.days_off.filter(date=day).exists():
        return None
    shift = profile.shifts.filter(weekday=day.weekday()).first()
    if shift is None:
        return None
    return (datetime.combine(day, shift.start_time, tzinfo=CAIRO), datetime.combine(day, shift.end_time, tzinfo=CAIRO))


def jobs_for(technician_user, day, exclude_order_id=None):
    from orders.models import Order

    start, end = local_day_bounds(day)
    qs = Order.blocking().filter(technician=technician_user, scheduled_start__gte=start, scheduled_start__lt=end)
    if exclude_order_id:
        qs = qs.exclude(pk=exclude_order_id)
    return [Job(o.scheduled_start, o.scheduled_end, (o.lat, o.lng)) for o in qs]
