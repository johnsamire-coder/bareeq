from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from scheduling.models import TechnicianProfile, WeeklyShift

from .helpers import WED, cairo, frozen_now, make_customer, make_technician, sid

NOW = cairo(WED - timedelta(days=1), 20)


class BookingApiTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.client = APIClient()
        self.client.force_authenticate(self.customer)
        self.body = {"address": self.address.id,
                     "items": [{"car": self.car.id, "services": sid("exterior-wash", "interior-wash")}]}

    def test_slots_then_book_then_confirm(self):
        with frozen_now(NOW):
            r = self.client.post("/api/booking/slots/", self.body, format="json")
            self.assertEqual(r.status_code, 200, r.content)
            wed = next(d for d in r.json()["days"] if d["date"] == WED.isoformat())
            first = wed["slots"][0]["start"]
            self.assertTrue(first.startswith("2026-11-18T09:00:00+02:00"), first)

            r = self.client.post("/api/orders/", {**self.body, "start": first}, format="json")
            self.assertEqual(r.status_code, 201, r.content)
            order = r.json()
            self.assertEqual(order["status"], "pending_payment")
            self.assertEqual(order["technician_name"], self.tech.full_name)
            self.assertEqual(order["total"], 24300)

            r = self.client.post(f"/api/orders/{order['id']}/confirm/", {"payment_method": "instapay"}, format="json")
            self.assertEqual(r.json()["code"], "payment_method_not_available")
            r = self.client.post(f"/api/orders/{order['id']}/confirm/", {"payment_method": "cash"}, format="json")
            self.assertEqual(r.json()["status"], "confirmed")

            # Same time again: taken (only one technician).
            r = self.client.post("/api/orders/", {**self.body, "start": first}, format="json")
            self.assertEqual(r.status_code, 409)
            self.assertEqual(r.json()["code"], "slot_taken")
        self.assertEqual(len(self.client.get("/api/orders/").json()), 1)

    def test_customer_sees_only_own_orders(self):
        with frozen_now(NOW):
            r = self.client.post("/api/orders/", {**self.body, "start": cairo(WED, 10).isoformat()}, format="json")
        oid = r.json()["id"]
        other, _, _ = make_customer("01012345670")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f"/api/orders/{oid}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/orders/{oid}/confirm/", {"payment_method": "cash"}).status_code, 404)

    def test_only_customers_book(self):
        self.client.force_authenticate(self.tech)
        self.assertEqual(self.client.post("/api/booking/slots/", self.body, format="json").status_code, 403)


class ManagerApiTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.t1 = make_technician("01100000001")
        self.t2 = make_technician("01100000002", home=(30.0300, 31.3800))
        self.customer, self.car, self.address = make_customer()
        self.client = APIClient()
        self.client.force_authenticate(self.customer)
        with frozen_now(NOW):
            r = self.client.post("/api/orders/", {
                "address": self.address.id, "start": cairo(WED, 10).isoformat(),
                "items": [{"car": self.car.id, "services": sid("exterior-wash")}]}, format="json")
        self.order_id = r.json()["id"]
        self.client.force_authenticate(self.manager)

    def test_day_list_and_reassign(self):
        rows = self.client.get("/api/manage/orders/", {"date": WED.isoformat()}).json()
        self.assertEqual([r["id"] for r in rows], [self.order_id])
        self.assertEqual(rows[0]["customer_phone"], "+201012345678")
        self.assertEqual(self.client.get("/api/manage/orders/", {"date": "2026-11-19"}).json(), [])
        with frozen_now(NOW):
            r = self.client.post(f"/api/manage/orders/{self.order_id}/reassign/", {"technician": self.t2.id}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["technician"], self.t2.id)

    def test_customer_cannot_use_manager_endpoints(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/manage/orders/").status_code, 403)
        self.assertEqual(self.client.get("/api/manage/technician-schedules/").status_code, 403)

    def test_schedule_editing(self):
        profile = self.t1.technician_profile
        r = self.client.get("/api/manage/technician-schedules/")
        self.assertEqual(len(r.json()), 2)
        shift = WeeklyShift.objects.filter(technician=profile, weekday=2).first()
        r = self.client.patch(f"/api/manage/technician-shifts/{shift.id}/", {"start_time": "12:00", "end_time": "11:00"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(f"/api/manage/technician-shifts/{shift.id}/", {"start_time": "12:00"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.delete(f"/api/manage/technician-shifts/{shift.id}/").status_code, 204)
        r = self.client.post("/api/manage/technician-days-off/", {"technician": profile.id, "date": "2026-11-20", "reason": "إجازة"}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.client.patch(f"/api/manage/technician-schedules/{profile.id}/", {"start_label": "المحل", "start_lat": "30.0500"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_technician_added_by_manager_gets_a_schedule_record(self):
        r = self.client.post("/api/technicians/", {"phone": "01122223333", "full_name": "جديد"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(TechnicianProfile.objects.filter(user_id=r.json()["id"]).exists())


class DemoTechniciansTests(TestCase):
    def test_seed(self):
        call_command("seed_demo_technicians", verbosity=0)
        call_command("seed_demo_technicians", verbosity=0)  # safe to run twice
        profiles = list(TechnicianProfile.objects.prefetch_related("zones", "shifts"))
        self.assertEqual(len(profiles), 5)
        zones = sorted(sorted(z.name for z in p.zones.all()) for p in profiles)
        self.assertEqual(zones.count(["مدينة نصر"]), 2)
        self.assertEqual(zones.count(["العبور", "مدينتي"]), 2)
        self.assertEqual(zones.count(["العبور", "مدينة نصر", "مدينتي"]), 1)
        days_off = []
        for p in profiles:
            worked = {s.weekday for s in p.shifts.all()}
            self.assertEqual(len(worked), 6)
            days_off += list(set(range(7)) - worked)
            self.assertTrue(all((s.start_time.hour, s.end_time.hour) == (9, 22) for s in p.shifts.all()))
        self.assertEqual(len(set(days_off)), 5)       # each a different day off
        self.assertNotIn(4, days_off)                 # everyone works on Friday
