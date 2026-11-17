"""Scheduling rules (SPEC section 6) as plain calculations, no database.

A technician's day is a shift (start, end) and the jobs already booked.
A new job of `duration` minutes at `place` can start at time t when:
- it is inside the shift: t >= shift start and t + duration <= shift end;
- after the previous job P (the last one starting at or before t):
      t >= max(P.end + travel(P.place, place) + buffer, P.start + min_gap)
  or, when it is the first job of the day: t >= shift start + travel(home, place);
- before the next job N (the first one starting after t):
      N.start >= max(t + duration + travel(place, N.place) + buffer, t + min_gap)

`travel(a, b)` returns whole minutes. Places can be anything the travel
function understands (here: (lat, lng) pairs; in tests: letters).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional


@dataclass(frozen=True)
class Config:
    buffer_minutes: int
    min_gap_minutes: int


@dataclass(frozen=True)
class Job:
    start: datetime
    end: datetime
    place: object


def _m(minutes):
    return timedelta(minutes=minutes)


def earliest_start_after(prev: Job, place, cfg: Config, travel: Callable) -> datetime:
    return max(
        prev.end + _m(travel(prev.place, place) + cfg.buffer_minutes),
        prev.start + _m(cfg.min_gap_minutes),
    )


def can_fit(t, duration, place, jobs, shift, home, cfg: Config, travel: Callable) -> bool:
    if shift is None:
        return False
    shift_start, shift_end = shift
    end = t + _m(duration)
    if t < shift_start or end > shift_end:
        return False

    prev: Optional[Job] = None
    nxt: Optional[Job] = None
    for job in sorted(jobs, key=lambda j: j.start):
        if job.start <= t:
            prev = job
        else:
            nxt = job
            break

    if prev is not None:
        if t < earliest_start_after(prev, place, cfg, travel):
            return False
    elif t < shift_start + _m(travel(home, place)):
        return False

    if nxt is not None:
        needed = max(end + _m(travel(place, nxt.place) + cfg.buffer_minutes), t + _m(cfg.min_gap_minutes))
        if nxt.start < needed:
            return False
    return True


def slot_grid(start: datetime, end: datetime, step_minutes: int):
    """Clock-aligned times (e.g. :00 and :30 for a 30-minute step) from start to end, inclusive."""
    midnight = start.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes = (start - midnight).total_seconds() / 60
    k = -(-int(minutes) // step_minutes)  # ceiling
    if k * step_minutes < minutes:
        k += 1
    t = midnight + _m(k * step_minutes)
    out = []
    while t <= end:
        out.append(t)
        t += _m(step_minutes)
    return out


def first_fit(from_time, duration, place, jobs, shift, home, cfg, travel, step_minutes):
    """Earliest clock-aligned start at or after from_time, or None."""
    if shift is None:
        return None
    for t in slot_grid(max(from_time, shift[0]), shift[1], step_minutes):
        if can_fit(t, duration, place, jobs, shift, home, cfg, travel):
            return t
    return None
