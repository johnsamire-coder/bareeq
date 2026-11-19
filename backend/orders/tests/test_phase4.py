"""Phase 4 (agreed with John 19 Nov 2026): technician tracking, the live map,
express orders, the distance fee, supervisors, detailed reports and Excel."""
import io
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from core.errors import BusinessError
from core.models import Setting
from coupons.models import Coupon
from coupons.service import apply_coupon
from feedback.models import Rating
from orders.booking import available_slots, create_order
from orders.lifecycle import arrived, complete_job, on_the_way
from orders.models import Order, TechnicianLocation
from orders.tests.helpers import CITY_STARS, WED, cairo, frozen_now, make_customer, make_technician, sid
from orders import tracking
from payments.payments import confirm_with_payment
from payments.tests.helpers import MEDIA, book, work_until_done_photos
from places.models import Address, Zone

NOW = cairo(WED, 10)


def setting(key, value):
    Setting.objects.filter(key=key).update(value=value)


class Base(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.items = [{"car": self.car.id, "services": sid("exterior-wash", "interior-wash")}]

    def confirmed(self, start, customer=None, address=None, car=None):
        o = book(customer or self.customer, car or self.car, address or self.address, start)
        with frozen_now(start - timedelta(days=1)):
            confirm_with_payment(o, "cash")
        o.refresh_from_db()
        return o


@override_settings(MEDIA_ROOT=MEDIA)
class TrackingTests(Base):
    def test_only_while_on_the_way(self):
        o = self.confirmed(cairo(WED, 12))
        with frozen_now(cairo(WED, 11)):
            self.assertEqual(tracking.report(self.tech, 30.07, 31.34), {"active": False, "interval_seconds": 30})
            self.assertFalse(TechnicianLocation.objects.exists())
            on_the_way(o, self.tech)
            self.assertTrue(tracking.report(self.tech, 30.08, 31.35, 12)["active"])
            api = APIClient()
            api.force_authenticate(self.customer)
            r = api.get(f"/api/orders/{o.id}/tracking/").json()
            self.assertEqual((r["active"], r["lat"], r["lng"], r["technician_name"]), (True, 30.08, 31.35, "فني 01"))
            self.assertGreaterEqual(r["eta_minutes"], 1)
        with frozen_now(cairo(WED, 11, 30)):
            arrived(o, self.tech)
            self.assertFalse(api.get(f"/api/orders/{o.id}/tracking/").json()["active"])
            self.assertEqual(tracking.report(self.tech, 30.09, 31.36)["active"], False)
        self.assertEqual(TechnicianLocation.objects.count(), 1)
        other, _, _ = make_customer("01012300000")
        api.force_authenticate(other)
        self.assertEqual(api.get(f"/api/orders/{o.id}/tracking/").status_code, 404)

    def test_old_points_deleted(self):
        o = self.confirmed(cairo(WED, 12))
        with frozen_now(cairo(WED, 11)):
            on_the_way(o, self.tech)
            tracking.report(self.tech, 30.08, 31.35)
        with frozen_now(cairo(WED, 11) + timedelta(days=8)):
            self.assertEqual(tracking.delete_old(), 1)

    def test_live_map_for_manager_and_supervisor(self):
        o = self.confirmed(cairo(WED, 12))
        with frozen_now(cairo(WED, 11)):
            on_the_way(o, self.tech)
            tracking.report(self.tech, 30.08, 31.35)
            api = APIClient()
            api.force_authenticate(self.manager)
            r = api.get("/api/manage/live-map/", {"date": WED.isoformat()}).json()
            self.assertEqual(r["technicians"][0]["lat"], 30.08)
            self.assertEqual([x["id"] for x in r["orders"]], [o.id])
            sup = User.objects.create_user("01000000002", "مشرف العبور", role="supervisor")
            from scheduling.models import SupervisorProfile

            SupervisorProfile.objects.create(user=sup).zones.set(Zone.objects.filter(name="العبور"))
            api.force_authenticate(sup)
            r = api.get("/api/manage/live-map/", {"date": WED.isoformat()}).json()
            self.assertEqual((r["orders"], r["technicians"]), ([], []))  # Nasr City is not his


@override_settings(MEDIA_ROOT=MEDIA)
class ExpressTests(Base):
    def test_someone_can_come_now(self):
        api = APIClient()
        api.force_authenticate(self.customer)
        with frozen_now(NOW + timedelta(minutes=2)):
            r = api.post("/api/booking/express/", {"address": self.address.id, "items": self.items},
                         format="json").json()
            self.assertEqual((r["available"], r["fee"]), (True, 5000))
            self.assertLessEqual(r["minutes_from_now"], 90)
            o = api.post("/api/orders/", {"address": self.address.id, "items": self.items, "start": r["start"],
                                          "express": True}, format="json").json()
        self.assertEqual((o["is_express"], o["express_fee"], o["amount_due"]), (True, 5000, 29300))

    def test_not_too_late_and_switch(self):
        with frozen_now(NOW), self.assertRaises(BusinessError) as e:
            create_order(self.customer, self.address.id, self.items, NOW + timedelta(hours=3), express=True)
        self.assertEqual(e.exception.detail["code"], "express_not_available")
        setting("express-enabled", False)
        api = APIClient()
        api.force_authenticate(self.customer)
        with frozen_now(NOW):
            self.assertFalse(api.post("/api/booking/express/", {"address": self.address.id, "items": self.items},
                                      format="json").json()["available"])

    def test_no_free_technician(self):
        with frozen_now(cairo(WED, 21, 30)):  # the shift ends at 22:00
            api = APIClient()
            api.force_authenticate(self.customer)
            self.assertFalse(api.post("/api/booking/express/", {"address": self.address.id, "items": self.items},
                                      format="json").json()["available"])


@override_settings(MEDIA_ROOT=MEDIA)
class DistanceFeeTests(Base):
    def far(self, lat):
        return Address.objects.create(customer=self.customer, label="بعيد", lat=lat, lng=CITY_STARS[1], building="2",
                                      zone=Zone.objects.get(name="مدينة نصر"))

    def test_free_near_then_per_km_then_max(self):
        near = book(self.customer, self.car, self.address, cairo(WED, 10))
        self.assertEqual(near.distance_fee, 0)
        o = book(self.customer, self.car, self.far(30.19), cairo(WED, 13))  # ~13 km: 4 km over x 5 = 20 EGP
        self.assertEqual((o.distance_fee, float(o.distance_km)), (2000, 13.0))
        self.assertEqual(o.amount_due, 24300 + 2000)
        o2 = book(self.customer, self.car, self.far(30.30), cairo(WED, 17))  # ~25 km: capped at 50
        self.assertEqual(o2.distance_fee, 5000)

    def test_shown_before_booking_and_not_discounted(self):
        far = self.far(30.19)
        with frozen_now(cairo(WED, 8)):
            s = available_slots(self.customer, far.id, self.items)
        self.assertEqual((s["distance_fee"], s["amount_due"]), (2000, 26300))
        o = book(self.customer, self.car, far, cairo(WED, 13))
        Coupon.objects.create(code="ALL", kind="percent", value=100, expires_at=cairo(WED, 23), max_uses_total=5,
                              max_uses_per_customer=1)
        with frozen_now(cairo(WED, 8)):
            o = apply_coupon(o, self.customer, "ALL")
        self.assertEqual(o.amount_due, 2000)  # services free, the fee stays

    def test_invoice_line(self):
        o = self.confirmed(cairo(WED, 13), address=self.far(30.19))
        end = work_until_done_photos(o, self.tech, o.scheduled_start)
        with frozen_now(end):
            o.refresh_from_db()
            complete_job(o, self.tech, cash_collected=o.amount_to_collect)
        inv = o.invoices.get()
        self.assertEqual((inv.fees_total, inv.total), (2000, 26300))
        self.assertEqual(inv.lines["fees"][0]["amount"], 2000)


@override_settings(MEDIA_ROOT=MEDIA)
class SupervisorTests(Base):
    def setUp(self):
        super().setUp()
        api = APIClient()
        api.force_authenticate(self.manager)
        nasr = Zone.objects.get(name="مدينة نصر")
        r = api.post("/api/manage/supervisors/", {"full_name": "مشرف مدينة نصر", "phone": "01200000001",
                                                  "zones": [nasr.id]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.sup = User.objects.get(phone="+201200000001")
        self.assertEqual(self.sup.role, "supervisor")
        self.api = APIClient()
        self.api.force_authenticate(self.sup)
        self.other_tech = make_technician("01100000002")
        self.obour_tech = make_technician("01100000003", zones=("العبور",))
        self.o = self.confirmed(cairo(WED, 12))

    def test_sees_his_zones_and_moves_jobs(self):
        rows = self.api.get("/api/manage/orders/", {"date": WED.isoformat()}).json()
        self.assertEqual([r["id"] for r in rows], [self.o.id])
        techs = {t["id"] for t in self.api.get("/api/manage/zone-technicians/").json()}
        self.assertEqual(techs, {self.tech.id, self.other_tech.id})
        new_tech = self.other_tech.id if self.o.technician_id == self.tech.id else self.tech.id
        with frozen_now(cairo(WED, 9)):
            r = self.api.post(f"/api/manage/orders/{self.o.id}/reassign/", {"technician": new_tech}, format="json")
            self.assertEqual(r.json()["technician"], new_tech)
            r = self.api.post(f"/api/manage/orders/{self.o.id}/reassign/", {"technician": self.obour_tech.id},
                              format="json")
            self.assertEqual(r.json()["code"], "not_your_zone")
            r = self.api.post(f"/api/manage/orders/{self.o.id}/reassign/", {"technician": new_tech, "force": True},
                              format="json")
            self.assertEqual(r.status_code, 403)
        self.assertEqual(self.api.post(f"/api/manage/orders/{self.o.id}/cancel/", {"reason": "x"},
                                       format="json").status_code, 403)

    def test_other_zone_hidden(self):
        sup2 = User.objects.create_user("01200000002", "مشرف العبور", role="supervisor")
        from scheduling.models import SupervisorProfile

        SupervisorProfile.objects.create(user=sup2).zones.set(Zone.objects.filter(name="العبور"))
        self.api.force_authenticate(sup2)
        self.assertEqual(self.api.get("/api/manage/orders/", {"date": WED.isoformat()}).json(), [])
        self.assertEqual(self.api.get(f"/api/manage/orders/{self.o.id}/").status_code, 404)

    def test_ratings_but_no_money(self):
        Rating.objects.create(order=self.o, customer=self.customer, technician=self.tech, zone=self.o.zone, stars=2)
        self.assertEqual(len(self.api.get("/api/manage/ratings/", {"bad": 1}).json()), 1)
        for url in ("/api/settings/", "/api/manage/payments/", "/api/manage/reports/", "/api/manage/daily-closings/",
                    "/api/manage/technician-custody/", "/api/manage/inbox/"):
            self.assertEqual(self.api.get(url).status_code, 403, url)

    def test_manager_changes_zones_and_stops(self):
        api = APIClient()
        api.force_authenticate(self.manager)
        r = api.patch(f"/api/manage/supervisors/{self.sup.id}/", {"zones": [], "is_active": False}, format="json")
        self.assertEqual((r.json()["zones"], r.json()["is_active"]), ([], False))
        self.assertEqual(api.post("/api/manage/supervisors/", {"full_name": "x", "phone": "01200000001"},
                                  format="json").json()["code"], "phone_taken")


@override_settings(MEDIA_ROOT=MEDIA)
class ReportsTests(Base):
    def test_technicians_zones_retention_and_excel(self):
        o = self.confirmed(cairo(WED, 10))
        end = work_until_done_photos(o, self.tech, o.scheduled_start)
        with frozen_now(end):
            o.refresh_from_db()
            complete_job(o, self.tech, cash_collected=o.amount_to_collect)
        Rating.objects.create(order=o, customer=self.customer, technician=self.tech, zone=o.zone, stars=5,
                              created_at=end)
        api = APIClient()
        api.force_authenticate(self.manager)
        q = {"from": WED.isoformat(), "to": WED.isoformat()}
        t = api.get("/api/manage/reports/technicians/", q).json()["rows"][0]
        self.assertEqual((t["completed"], t["on_time_percent"], t["avg_actual_minutes"], t["avg_planned_minutes"],
                          t["revenue"], t["rating_avg"]), (1, 100, 85, 85, 24300, 5.0))
        z = api.get("/api/manage/reports/zones/", q).json()["rows"][0]
        self.assertEqual((z["name"], z["orders"], z["new_customers"]), ("مدينة نصر", 1, 1))
        later = {"from": WED.isoformat(), "to": (WED + timedelta(days=40)).isoformat()}
        r = api.get("/api/manage/reports/retention/", later).json()
        self.assertEqual((r["served"], r["first_time"], r["lost"]), (1, 1, 1))
        for kind in ("summary", "technicians", "zones", "retention"):
            link = api.post("/api/manage/reports/export/", {"report": kind, **q}, format="json").json()["url"]
            path = link.split("testserver")[1]
            f = self.client.get(path)
            self.assertEqual(f.status_code, 200, kind)
            from openpyxl import load_workbook

            wb = load_workbook(io.BytesIO(f.content))
            self.assertTrue(wb.worksheets[0].sheet_view.rightToLeft)
        self.assertEqual(self.client.get("/api/reports/download/bad-token/").status_code, 403)
        api.force_authenticate(self.customer)
        self.assertEqual(api.post("/api/manage/reports/export/", {"report": "summary"}, format="json").status_code, 403)
