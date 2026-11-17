"""Available slots, temporary hold, auto-assign and moving a job (SPEC 6).

Clock: 'now' is frozen at Tuesday 17 Nov 2026, 20:00 Cairo; we book for
Wednesday 18 Nov. Basic bundle (exterior + interior) on a sedan = 85 minutes.
"""
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase

from cars.models import CarModel, CustomerCar
from core.errors import BusinessError
from core.models import Setting
from orders.booking import available_slots, confirm_order, create_order, expire_holds, reassign
from orders.models import Order
from places.models import Address
from scheduling.models import DayOff

from .helpers import CITY_STARS, WED, cairo, frozen_now, make_customer, make_technician, sid

NOW = cairo(WED - timedelta(days=1), 20)
BASIC = ["exterior-wash", "interior-wash"]


def slots_on(result, day):
    for d in result["days"]:
        if d["date"] == day.isoformat():
            return {s["start"].astimezone(cairo(WED, 0).tzinfo).strftime("%H:%M"): s["free_technicians"] for s in d["slots"]}
    return {}


class SlotsTests(TestCase):
    def setUp(self):
        self.customer, self.car, self.address = make_customer()
        self.items = [{"car": self.car.id, "services": sid(*BASIC)}]

    def slots(self, now=NOW):
        with frozen_now(now):
            return available_slots(self.customer, self.address.id, self.items)

    def test_one_free_technician_whole_day(self):
        make_technician("01100000001")
        r = self.slots()
        self.assertEqual(r["total_minutes"], 85)
        self.assertEqual(r["total"], 24300)
        wed = slots_on(r, WED)
        # Travel from home is 0 (same spot): 9:00 is fine. Must end by 22:00 -> last start 20:30.
        self.assertEqual(min(wed), "09:00")
        self.assertEqual(max(wed), "20:30")
        self.assertEqual(len(wed), 24)
        self.assertEqual(set(wed.values()), {1})

    def test_days_ahead_and_min_notice(self):
        make_technician("01100000001")
        r = self.slots()
        self.assertEqual(len(r["days"]), 7)  # setting: 7 days
        # Today (Tuesday) at 20:00: +60 min notice = 21:00, and 85 min does not fit before 22:00.
        self.assertEqual(slots_on(r, WED - timedelta(days=1)), {})
        r = self.slots(now=cairo(WED, 10, 10))
        self.assertEqual(min(slots_on(r, WED)), "11:30")  # 10:10 + 60 = 11:10 -> next grid time 11:30

    def test_no_technician_for_zone_or_day(self):
        make_technician("01100000001", zones=("العبور",))
        self.assertEqual(slots_on(self.slots(), WED), {})
        tech = make_technician("01100000002", weekdays=[0, 1, 3, 4, 5, 6])  # Wednesday off
        self.assertEqual(slots_on(self.slots(), WED), {})
        DayOff.objects.create(technician=tech.technician_profile, date=WED + timedelta(days=1))
        self.assertEqual(slots_on(self.slots(), WED + timedelta(days=1)), {})

    def test_inactive_technician_or_no_start_point_ignored(self):
        tech = make_technician("01100000001")
        tech.is_active = False
        tech.save()
        self.assertEqual(slots_on(self.slots(), WED), {})
        tech2 = make_technician("01100000002")
        tech2.technician_profile.start_lat = None
        tech2.technician_profile.save()
        self.assertEqual(slots_on(self.slots(), WED), {})

    def test_booked_job_blocks_with_min_gap(self):
        tech = make_technician("01100000001")
        other, ocar, oaddr = make_customer("01012345670")
        with frozen_now(NOW):
            o = create_order(other, oaddr.id, [{"car": ocar.id, "services": sid("exterior-wash")}], cairo(WED, 10))
            confirm_order(o, "cash")
        wed = slots_on(self.slots(), WED)
        # Before 10:00: 9:00 + 85 + 15 buffer = 10:40 > 10:00 -> nothing.
        # After: max(10:45 + 0 + 15 = 11:00, 10:00 + 90 = 11:30) -> 11:30.
        self.assertEqual(min(wed), "11:30")
        self.assertEqual(o.technician, tech)

    def test_two_technicians_count(self):
        make_technician("01100000001")
        make_technician("01100000002")
        self.assertEqual(slots_on(self.slots(), WED)["10:00"], 2)
        with frozen_now(NOW):
            create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
        wed = slots_on(self.slots(), WED)
        self.assertEqual(wed["10:00"], 1)
        self.assertEqual(wed["09:00"], 1)

    def test_settings_change_slots(self):
        make_technician("01100000001")
        Setting.objects.filter(key="scheduling-slot-step-minutes").update(value=60)
        wed = slots_on(self.slots(), WED)
        self.assertEqual(sorted(wed)[:2], ["09:00", "10:00"])
        Setting.objects.filter(key="scheduling-days-ahead").update(value=2)
        self.assertEqual(len(self.slots()["days"]), 2)


class HoldAndConfirmTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.items = [{"car": self.car.id, "services": sid(*BASIC)}]

    def test_hold_lasts_10_minutes(self):
        with frozen_now(NOW):
            o = create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
        self.assertEqual(o.status, "pending_payment")
        self.assertEqual(o.hold_expires_at, NOW + timedelta(minutes=10))
        self.assertEqual(o.scheduled_end, cairo(WED, 11, 25))
        self.assertEqual(o.total, 24300)
        # While held, nobody else gets 10:00.
        other, ocar, oaddr = make_customer("01012345670")
        with frozen_now(NOW + timedelta(minutes=9)):
            with self.assertRaises(BusinessError) as e:
                create_order(other, oaddr.id, [{"car": ocar.id, "services": sid(*BASIC)}], cairo(WED, 10))
            self.assertEqual(e.exception.detail["code"], "slot_taken")
        # After 10 minutes without payment the time is free again.
        with frozen_now(NOW + timedelta(minutes=11)):
            o2 = create_order(other, oaddr.id, [{"car": ocar.id, "services": sid(*BASIC)}], cairo(WED, 10))
            self.assertEqual(o2.technician, self.tech)
            with self.assertRaises(BusinessError) as e:
                confirm_order(o, "cash")
            self.assertEqual(e.exception.detail["code"], "hold_expired")

    def test_confirm_in_time(self):
        with frozen_now(NOW):
            o = create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
        with frozen_now(NOW + timedelta(minutes=5)):
            confirm_order(o, "cash")
        o.refresh_from_db()
        self.assertEqual((o.status, o.payment_method, o.hold_expires_at), ("confirmed", "cash", None))
        # A confirmed order keeps blocking forever.
        other, ocar, oaddr = make_customer("01012345670")
        with frozen_now(NOW + timedelta(hours=2)):
            with self.assertRaises(BusinessError):
                create_order(other, oaddr.id, [{"car": ocar.id, "services": sid(*BASIC)}], cairo(WED, 10))

    def test_hold_minutes_is_a_setting(self):
        Setting.objects.filter(key="scheduling-slot-hold-minutes").update(value=3)
        with frozen_now(NOW):
            o = create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
        self.assertEqual(o.hold_expires_at, NOW + timedelta(minutes=3))

    def test_expire_holds_marks_orders(self):
        with frozen_now(NOW):
            o = create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
        with frozen_now(NOW + timedelta(minutes=11)):
            self.assertEqual(expire_holds(), 1)
            call_command("expire_holds", verbosity=0)
        o.refresh_from_db()
        self.assertEqual(o.status, "expired")


class BookingValidationTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()

    def book(self, items=None, start=None, address=None, customer=None, now=NOW):
        with frozen_now(now):
            return create_order(customer or self.customer, address or self.address.id,
                                items if items is not None else [{"car": self.car.id, "services": sid(*BASIC)}],
                                start or cairo(WED, 10))

    def code(self, **kw):
        with self.assertRaises(BusinessError) as e:
            self.book(**kw)
        return e.exception.detail["code"]

    def test_bad_requests(self):
        other, ocar, oaddr = make_customer("01012345670")
        self.assertEqual(self.code(items=[]), "no_cars")
        self.assertEqual(self.code(items=[{"car": ocar.id, "services": sid("exterior-wash")}]), "car_not_found")
        self.assertEqual(self.code(address=oaddr.id), "address_not_found")
        self.assertEqual(self.code(start=cairo(WED, 10, 10)), "invalid_slot")      # not on the 30-min grid
        self.assertEqual(self.code(start=cairo(WED - timedelta(days=1), 20, 30)), "invalid_slot")  # too soon
        self.assertEqual(self.code(start=cairo(WED + timedelta(days=8), 10)), "invalid_slot")      # too far
        self.assertEqual(self.code(start=cairo(WED, 21)), "slot_taken")  # 85 min does not fit before 22:00
        same = {"car": self.car.id, "services": sid("exterior-wash")}
        self.assertEqual(self.code(items=[same, same]), "duplicate_car")

    def test_address_outside_zones(self):
        Address.objects.filter(pk=self.address.id).update(zone=None)
        self.assertEqual(self.code(), "outside_service_area")

    def test_two_cars_one_order(self):
        m = CarModel.objects.get(brand__name_en="Hyundai", name="Tucson")  # SUV
        car2 = CustomerCar.objects.create(customer=self.customer, brand=m.brand, model=m, year=2022,
                                          color=self.car.color, parking="street")
        o = self.book(items=[{"car": self.car.id, "services": sid(*BASIC)},
                             {"car": car2.id, "services": sid("exterior-wash")}])
        self.assertEqual(o.items.count(), 2)
        self.assertEqual(o.total_minutes, 85 + 55)
        self.assertEqual(o.total, 24300 + 18000)
        self.assertEqual(o.scheduled_end, cairo(WED, 12, 20))


class AutoAssignAndMoveTests(TestCase):
    def setUp(self):
        self.customer, self.car, self.address = make_customer()
        self.items = [{"car": self.car.id, "services": sid(*BASIC)}]

    def test_nearest_technician_gets_the_job(self):
        far = make_technician("01100000001", home=(30.0300, 31.3800))   # few km away
        near = make_technician("01100000002", home=(30.0735, 31.3460))  # next door
        with frozen_now(NOW):
            o = create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
        self.assertEqual(o.technician, near)
        # Next booking at the same time goes to the one still free.
        other, ocar, oaddr = make_customer("01012345670")
        with frozen_now(NOW):
            o2 = create_order(other, oaddr.id, [{"car": ocar.id, "services": sid(*BASIC)}], cairo(WED, 10))
        self.assertEqual(o2.technician, far)

    def test_manager_moves_job(self):
        t1 = make_technician("01100000001")
        t2 = make_technician("01100000002", home=(30.0300, 31.3800))
        t3 = make_technician("01100000003", zones=("العبور",))
        with frozen_now(NOW):
            o = create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
            confirm_order(o, "cash")
        self.assertEqual(o.technician, t1)
        with frozen_now(NOW):
            reassign(o, t2)
        o.refresh_from_db()
        self.assertEqual(o.technician, t2)
        # t3 does not cover Nasr City: refused unless forced.
        with frozen_now(NOW):
            with self.assertRaises(BusinessError) as e:
                reassign(o, t3)
            self.assertEqual(e.exception.detail["code"], "technician_not_available")
            reassign(o, t3, force=True)
        o.refresh_from_db()
        self.assertEqual(o.technician, t3)

    def test_cannot_move_to_busy_technician(self):
        t1 = make_technician("01100000001")
        t2 = make_technician("01100000002", home=(30.0300, 31.3800))
        other, ocar, oaddr = make_customer("01012345670")
        with frozen_now(NOW):
            a = create_order(self.customer, self.address.id, self.items, cairo(WED, 10))
            b = create_order(other, oaddr.id, [{"car": ocar.id, "services": sid(*BASIC)}], cairo(WED, 10))
            self.assertEqual({a.technician, b.technician}, {t1, t2})
            with self.assertRaises(BusinessError):
                reassign(a, b.technician)
