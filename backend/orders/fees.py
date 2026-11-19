"""Extra fees on an order (phase 4, numbers agreed with John 19 Nov 2026; all settings).

- Distance fee: free up to N km (straight line) from the nearest technician's
  start point in the zone, then X per km, at most Y. Whole pounds.
- Express fee: «عايز حد دلوقتي», when a technician can arrive within the
  setting's minutes.
Fees are never discounted (discounts are on services only).
"""
import math
from datetime import timedelta

from django.utils import timezone

from core.errors import BusinessError
from core.services import get_setting
from scheduling.availability import config, jobs_for, schedulable_technicians, shift_for, travel_function, CAIRO
from scheduling.engine import first_fit
from scheduling.travel import distance_km


def nearest_km(zone, place):
    homes = [p.home for p in schedulable_technicians(zone)]
    if not homes:
        return None
    return min(distance_km(place, h) for h in homes)


def distance_fee(zone, place):
    """(fee in piastres, km rounded to 0.1 or None)."""
    km = nearest_km(zone, place)
    if km is None:
        return 0, None
    free = get_setting("distance-fee-free-km")
    if km <= free:
        return 0, round(km, 1)
    fee = math.ceil(km - free) * get_setting("distance-fee-per-km")
    return min(fee, get_setting("distance-fee-max")), round(km, 1)


def express_option(prep, now=None):
    """The earliest start a technician can make from now, within the express
    limit: {"start", "technician", "fee"} or None."""
    if not get_setting("express-enabled"):
        return None
    now = now or timezone.now()
    latest = now + timedelta(minutes=get_setting("scheduling-express-max-arrival-minutes"))
    day = now.astimezone(CAIRO).date()
    from scheduling.models import is_closed

    if is_closed(prep.zone, day):
        return None
    cfg, travel = config(), travel_function()
    best = None
    for profile in schedulable_technicians(prep.zone):
        shift = shift_for(profile, day)
        t = first_fit(now, prep.minutes, prep.place, jobs_for(profile.user, day), shift, profile.home, cfg, travel,
                      get_setting("express-time-step-minutes"))
        if t is not None and t <= latest and (best is None or t < best[0]):
            best = (t, profile.user)
    if best is None:
        return None
    return {"start": best[0], "technician": best[1], "fee": get_setting("express-fee")}


def check_express_start(prep, start, now=None):
    now = now or timezone.now()
    opt = express_option(prep, now)
    if opt is None:
        raise BusinessError("express_not_available", "مفيش فني يقدر يوصلك دلوقتي. احجز ميعاد عادي.")
    latest = now + timedelta(minutes=get_setting("scheduling-express-max-arrival-minutes"))
    if not (now <= start <= latest):
        raise BusinessError("express_not_available", "الميعاد ده مش متاح للطلب السريع.")
    return opt
