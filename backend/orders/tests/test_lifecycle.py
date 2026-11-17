"""Technician flow: on the way -> arrived -> (4 'before' photos) start ->
(4 'after' photos) done. 'Car not found' only after calling the customer and
waiting 15 minutes (setting); it records time + place and charges 50 EGP."""
from datetime import timedelta

from django.test import TestCase, override_settings

from accounts.models import User
from core.errors import BusinessError
from orders.lifecycle import (
    arrived,
    called_customer,
    car_not_found,
    cancel_by_company,
    complete_job,
    on_the_way,
    start_job,
)
from orders.models import CustomerCharge, OrderEvent
from orders.photos import add_photo

from .helpers import CITY_STARS, WED, book_confirmed, cairo, frozen_now, jpeg_bytes, make_customer, make_technician

SIDES = ["front", "back", "left", "right"]


def shoot(order, tech, stage, sides=SIDES, when=None):
    for side in sides:
        add_photo(order, tech, stage, side, jpeg_bytes(), captured_at=when or cairo(WED, 14), lat=CITY_STARS[0],
                  lng=CITY_STARS[1], accuracy_m=8)


@override_settings(MEDIA_ROOT=__import__("tempfile").mkdtemp())
class TechnicianFlowTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.order = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))

    def test_full_happy_path(self):
        with frozen_now(cairo(WED, 13, 40)):
            on_the_way(self.order, self.tech)
        with frozen_now(cairo(WED, 13, 58)):
            arrived(self.order, self.tech, lat=CITY_STARS[0], lng=CITY_STARS[1])
        with frozen_now(cairo(WED, 14)):
            with self.assertRaises(BusinessError) as e:
                start_job(self.order, self.tech)
            self.assertEqual(e.exception.detail["code"], "before_photos_missing")
            shoot(self.order, self.tech, "before", SIDES[:3])
            with self.assertRaises(BusinessError):
                start_job(self.order, self.tech)
            shoot(self.order, self.tech, "before", SIDES[3:])
            start_job(self.order, self.tech)
        with frozen_now(cairo(WED, 14, 50)):
            with self.assertRaises(BusinessError) as e:
                complete_job(self.order, self.tech)
            self.assertEqual(e.exception.detail["code"], "after_photos_missing")
            shoot(self.order, self.tech, "after", when=cairo(WED, 14, 50))
            complete_job(self.order, self.tech)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "completed")
        self.assertEqual((self.order.actual_start, self.order.actual_end), (cairo(WED, 14), cairo(WED, 14, 50)))
        self.assertEqual(list(OrderEvent.objects.filter(order=self.order).values_list("to_status", flat=True)),
                         ["on_the_way", "arrived", "in_progress", "completed"])

    def test_steps_cannot_be_skipped(self):
        with self.assertRaises(BusinessError):
            arrived(self.order, self.tech)
        with self.assertRaises(BusinessError):
            start_job(self.order, self.tech)
        with self.assertRaises(BusinessError):
            complete_job(self.order, self.tech)

    def test_only_the_assigned_technician(self):
        other = make_technician("01100000002")
        with self.assertRaises(BusinessError) as e:
            on_the_way(self.order, other)
        self.assertEqual(e.exception.detail["code"], "not_your_job")

    def test_company_cancel_is_free_and_needs_reason(self):
        manager = User.objects.create_user("01000000001", "Boss", role="manager")
        with self.assertRaises(BusinessError):
            cancel_by_company(self.order, manager, "")
        cancel_by_company(self.order, manager, "مطر شديد")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled_by_company")
        self.assertFalse(CustomerCharge.objects.exists())


class CarNotFoundTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.order = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))
        with frozen_now(cairo(WED, 13, 40)):
            on_the_way(self.order, self.tech)
        with frozen_now(cairo(WED, 14)):
            arrived(self.order, self.tech)

    def test_needs_call_then_15_minutes(self):
        with frozen_now(cairo(WED, 14, 1)):
            with self.assertRaises(BusinessError) as e:
                car_not_found(self.order, self.tech, lat=30.07, lng=31.34)
            self.assertEqual(e.exception.detail["code"], "call_customer_first")
            called_customer(self.order, self.tech)
        with frozen_now(cairo(WED, 14, 15)):
            with self.assertRaises(BusinessError) as e:
                car_not_found(self.order, self.tech, lat=30.07, lng=31.34)
            self.assertEqual(e.exception.detail["code"], "wait_more")
        with frozen_now(cairo(WED, 14, 16)):
            car_not_found(self.order, self.tech, lat=30.07, lng=31.34)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "car_not_found")
        event = OrderEvent.objects.get(order=self.order, to_status="car_not_found")
        self.assertEqual((event.at, float(event.lat), float(event.lng)), (cairo(WED, 14, 16), 30.07, 31.34))
        charge = CustomerCharge.objects.get()
        self.assertEqual((charge.kind, charge.amount), ("car_not_found", 5000))

    def test_needs_location(self):
        with frozen_now(cairo(WED, 14, 1)):
            called_customer(self.order, self.tech)
        with frozen_now(cairo(WED, 14, 30)):
            with self.assertRaises(BusinessError):
                car_not_found(self.order, self.tech, lat=None, lng=None)
