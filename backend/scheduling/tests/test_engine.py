"""Scheduling rules (SPEC section 6), tested on the pure calculation with a
fake travel-time table, so every number is known in advance.

Rule: earliest next start after job P at place X =
    max(P.end + travel(P.place -> X) + buffer, P.start + min_gap)
First job of the day: shift start + travel(home -> X).
"""
from datetime import datetime, timedelta

from django.test import SimpleTestCase

from scheduling.engine import Config, Job, can_fit, earliest_start_after, first_fit, slot_grid

DAY = datetime(2026, 11, 18)  # a Wednesday; times are naive here (the engine does not care)


def at(h, m=0):
    return DAY.replace(hour=h, minute=m)


HOME, A, B, C, D = "home", "A", "B", "C", "D"

# Minutes between places (both directions).
TRAVEL = {
    frozenset({A, B}): 20,
    frozenset({B, C}): 25,
    frozenset({A, C}): 30,
    frozenset({HOME, A}): 10,
    frozenset({HOME, B}): 15,
    frozenset({HOME, C}): 20,
    frozenset({A, D}): 5,
    frozenset({HOME, D}): 5,
    frozenset({B, D}): 20,
    frozenset({C, D}): 30,
}


def travel(a, b):
    return 0 if a == b else TRAVEL[frozenset({a, b})]


CFG = Config(buffer_minutes=15, min_gap_minutes=90)
SHIFT = (at(9), at(22))


class SpecExampleTests(SimpleTestCase):
    """The example written in docs/SPEC.md, section 6."""

    def test_after_short_job_min_gap_wins(self):
        a = Job(at(10), at(10, 45), A)  # exterior wash 45 min
        # 10:45 + 20 travel + 15 buffer = 11:20, but 10:00 + 90 = 11:30 -> 11:30
        self.assertEqual(earliest_start_after(a, B, CFG, travel), at(11, 30))

    def test_after_long_job_travel_wins(self):
        b = Job(at(11, 30), at(14, 30), B)  # exterior detailing 180 min
        # 14:30 + 25 + 15 = 15:10; 11:30 + 90 = 13:00 -> 15:10 (not 13:00)
        self.assertEqual(earliest_start_after(b, C, CFG, travel), at(15, 10))

    def test_whole_day_chain(self):
        jobs = [Job(at(10), at(10, 45), A), Job(at(11, 30), at(14, 30), B)]
        self.assertTrue(can_fit(at(15, 10), 45, C, jobs, SHIFT, HOME, CFG, travel))
        self.assertFalse(can_fit(at(15, 5), 45, C, jobs, SHIFT, HOME, CFG, travel))
        self.assertEqual(first_fit(at(9), 45, C, jobs, SHIFT, HOME, CFG, travel, step_minutes=5), at(15, 10))


class FirstJobTests(SimpleTestCase):
    def test_first_job_needs_travel_from_home(self):
        self.assertFalse(can_fit(at(9), 45, C, [], SHIFT, HOME, CFG, travel))       # 20 min from home
        self.assertFalse(can_fit(at(9, 15), 45, C, [], SHIFT, HOME, CFG, travel))
        self.assertTrue(can_fit(at(9, 20), 45, C, [], SHIFT, HOME, CFG, travel))

    def test_job_must_end_by_shift_end(self):
        self.assertTrue(can_fit(at(21, 15), 45, A, [], SHIFT, HOME, CFG, travel))   # ends 22:00
        self.assertFalse(can_fit(at(21, 30), 45, A, [], SHIFT, HOME, CFG, travel))  # ends 22:15
        # A 3-hour job cannot start at 19:30.
        self.assertFalse(can_fit(at(19, 30), 180, A, [], SHIFT, HOME, CFG, travel))
        self.assertTrue(can_fit(at(19), 180, A, [], SHIFT, HOME, CFG, travel))

    def test_no_shift_no_work(self):
        self.assertFalse(can_fit(at(10), 45, A, [], None, HOME, CFG, travel))


class InsertBetweenJobsTests(SimpleTestCase):
    """A new job between two booked jobs must respect BOTH neighbours."""

    def setUp(self):
        self.jobs = [Job(at(10), at(10, 45), A), Job(at(14), at(14, 45), B)]

    def test_fits_in_the_middle(self):
        # After A: max(10:45+5+15=11:05, 10:00+90=11:30) = 11:30.
        # Before B: start + 45 + travel D->B 20 + 15 <= 14:00 -> start <= 12:40;
        # and start + 90 <= 14:00 -> start <= 12:30.
        self.assertFalse(can_fit(at(11, 25), 45, D, self.jobs, SHIFT, HOME, CFG, travel))
        self.assertTrue(can_fit(at(11, 30), 45, D, self.jobs, SHIFT, HOME, CFG, travel))
        self.assertTrue(can_fit(at(12, 30), 45, D, self.jobs, SHIFT, HOME, CFG, travel))
        self.assertFalse(can_fit(at(12, 35), 45, D, self.jobs, SHIFT, HOME, CFG, travel))

    def test_too_long_for_the_gap(self):
        # 2-hour job after 11:30 would end 13:30 + 20 + 15 = 14:05 > 14:00.
        self.assertFalse(can_fit(at(11, 30), 120, D, self.jobs, SHIFT, HOME, CFG, travel))

    def test_before_first_booked_job(self):
        # New job at D before A (10:00): start + 45 + 5 + 15 <= 10:00 and start + 90 <= 10:00.
        self.assertTrue(can_fit(at(8, 30), 45, D, self.jobs, (at(8), at(22)), HOME, CFG, travel))
        self.assertFalse(can_fit(at(8, 35), 45, D, self.jobs, (at(8), at(22)), HOME, CFG, travel))

    def test_overlap_is_never_allowed(self):
        self.assertFalse(can_fit(at(10, 15), 15, A, self.jobs, SHIFT, HOME, CFG, travel))

    def test_settings_change_the_answer(self):
        cfg = Config(buffer_minutes=0, min_gap_minutes=0)
        # After A: 10:45 + 5 = 10:50.
        self.assertTrue(can_fit(at(10, 50), 45, D, self.jobs, SHIFT, HOME, cfg, travel))
        self.assertFalse(can_fit(at(10, 50), 45, D, self.jobs, SHIFT, HOME, CFG, travel))


class GridTests(SimpleTestCase):
    def test_grid_inside_shift(self):
        grid = slot_grid(at(9), at(11), 30)
        self.assertEqual(grid, [at(9), at(9, 30), at(10), at(10, 30), at(11)])

    def test_grid_aligned_to_clock(self):
        self.assertEqual(slot_grid(at(9, 10), at(10), 30), [at(9, 30), at(10)])
