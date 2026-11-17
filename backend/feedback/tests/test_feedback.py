"""Ratings (SPEC 10), damage reports within 24 hours, and closing a day or a
zone because of the weather (orders cancelled free, customer gets a
'book a new time' button)."""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from core.errors import BusinessError
from feedback.models import DamageReport, Rating, RatingTag
from feedback.service import add_rating, close_day, report_damage
from notifications.models import Notification
from orders.booking import available_slots, create_order
from orders.lifecycle import complete_job
from orders.models import Order
from orders.tests.helpers import WED, cairo, frozen_now, jpeg_bytes, make_customer, make_technician, sid
from payments import wallet
from payments.payments import confirm_with_payment
from payments.tests.helpers import MEDIA, book, work_until_done_photos
from places.models import Zone

START = cairo(WED, 10)
BEFORE = START - timedelta(days=1)


@override_settings(MEDIA_ROOT=MEDIA)
class RatingTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "cash")
        self.end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(self.end):
            complete_job(self.order, self.tech, cash_collected=self.order.amount_due)
        self.tags = list(RatingTag.objects.all())

    def test_tags_seeded(self):
        self.assertEqual([t.name for t in self.tags], ["في الميعاد", "جودة الشغل", "الأخلاق", "النضافة حوالين العربية"])

    def test_good_rating_and_google_prompt(self):
        r, extra = add_rating(self.order, self.customer, 5, [self.tags[0].id, self.tags[1].id], "ممتاز")
        self.assertEqual((r.stars, r.technician, r.zone), (5, self.tech, self.order.zone))
        self.assertEqual(r.tags.count(), 2)
        self.assertIn("[مؤقت]", extra["google_review_link"])
        self.assertFalse(Notification.objects.filter(user=self.manager).exists())

    def test_bad_rating_alerts_manager_and_allows_call_request(self):
        r, extra = add_rating(self.order, self.customer, 3, [], "اتأخر", call_requested=True)
        self.assertIsNone(extra.get("google_review_link"))
        self.assertTrue(r.is_bad)
        n = Notification.objects.get(user=self.manager, kind="bad_rating")
        self.assertIn("كلمني", n.body)

    def test_rules(self):
        with self.assertRaises(BusinessError):
            add_rating(self.order, self.customer, 6, [])
        other, _, _ = make_customer("01012345670")
        with self.assertRaises(BusinessError):
            add_rating(self.order, other, 5, [])
        add_rating(self.order, self.customer, 4, [])
        with self.assertRaises(BusinessError):
            add_rating(self.order, self.customer, 5, [])  # once per order

    def test_not_before_completion(self):
        o2 = book(self.customer, self.car, self.address, cairo(WED, 16))
        with self.assertRaises(BusinessError):
            add_rating(o2, self.customer, 5, [])

    def test_api_summary_and_handling(self):
        c = APIClient()
        c.force_authenticate(self.customer)
        r = c.post(f"/api/orders/{self.order.id}/rating/", {"stars": 2, "tags": [self.tags[0].id], "comment": "وحش",
                                                             "call_requested": True}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        rid = r.json()["rating"]["id"]
        r = c.post(f"/api/ratings/{rid}/photos/", {"image": SimpleUploadedFile("a.jpg", jpeg_bytes(), "image/jpeg")},
                   format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        c.force_authenticate(self.manager)
        rows = c.get("/api/manage/ratings/", {"bad": 1, "unhandled": 1}).json()
        self.assertEqual([x["id"] for x in rows], [rid])
        self.assertTrue(rows[0]["call_requested"])
        self.assertEqual(len(rows[0]["photos"]), 1)
        self.assertEqual(c.get(rows[0]["photos"][0]).status_code, 200)  # manager opens the customer's photo
        s = c.get("/api/manage/ratings/summary/").json()
        self.assertEqual(s["by_technician"][0]["average"], 2.0)
        self.assertEqual(s["by_zone"][0]["zone"], "مدينة نصر")
        self.assertEqual({x["service"] for x in s["by_service"]}, {"غسيل خارجي", "غسيل داخلي"})
        self.assertEqual(c.post(f"/api/manage/ratings/{rid}/handle/", {"note": ""}, format="json").status_code, 400)
        c.post(f"/api/manage/ratings/{rid}/handle/", {"note": "كلمناه واعتذرنا"}, format="json")
        self.assertEqual(c.get("/api/manage/ratings/", {"bad": 1, "unhandled": 1}).json(), [])


@override_settings(MEDIA_ROOT=MEDIA)
class DamageReportTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "cash")
        self.end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(self.end):
            complete_job(self.order, self.tech, cash_collected=self.order.amount_due)

    def test_within_24_hours_only(self):
        with frozen_now(self.end + timedelta(hours=23, minutes=59)):
            d = report_damage(self.order, self.customer, "خدش في الباب")
        self.assertEqual(d.status, "open")
        self.assertEqual(Notification.objects.get(user=self.manager).kind, "damage_report")
        with frozen_now(self.end + timedelta(hours=24, minutes=1)):
            with self.assertRaises(BusinessError) as e:
                report_damage(self.order, self.customer, "تاني")
        self.assertEqual(e.exception.detail["code"], "report_window_closed")

    def test_needs_text_and_own_completed_order(self):
        with frozen_now(self.end):
            with self.assertRaises(BusinessError):
                report_damage(self.order, self.customer, "  ")
            other, _, _ = make_customer("01012345670")
            with self.assertRaises(BusinessError):
                report_damage(self.order, other, "x")

    def test_api_with_photos_and_resolve(self):
        c = APIClient()
        c.force_authenticate(self.customer)
        with frozen_now(self.end + timedelta(hours=2)):
            r = c.post(f"/api/orders/{self.order.id}/damage-report/", {"description": "خدش"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        did = r.json()["id"]
        r = c.post(f"/api/damage-reports/{did}/photos/", {"image": SimpleUploadedFile("a.jpg", jpeg_bytes(), "image/jpeg")},
                   format="multipart")
        self.assertEqual(r.status_code, 201)
        c.force_authenticate(self.manager)
        rows = c.get("/api/manage/damage-reports/", {"status": "open"}).json()
        self.assertEqual(len(rows[0]["photos"]), 1)
        c.post(f"/api/manage/damage-reports/{did}/resolve/", {"note": "راجعنا الصور: الخدش كان موجود قبل"}, format="json")
        self.assertEqual(DamageReport.objects.get().status, "resolved")


class CloseDayTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001", zones=("مدينة نصر", "مدينتي"))
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        with frozen_now(BEFORE - timedelta(days=1)):
            wallet.credit(self.customer, 10000, "manual", created_by=self.manager, note="x")
        self.order = book(self.customer, self.car, self.address, START)
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "cash", wallet_amount=5000)

    def test_close_zone_day_cancels_free_and_offers_rebook(self):
        with frozen_now(BEFORE):
            n, _ = close_day(WED, Zone.objects.get(name="مدينة نصر"), "مطر شديد", self.manager)
        self.assertEqual(n, 1)
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.cancel_reason), ("cancelled_by_company", "مطر شديد"))
        with frozen_now(BEFORE):
            self.assertEqual(wallet.balance(self.customer), 10000)  # wallet part came back
        note = Notification.objects.get(user=self.customer, kind="day_closed")
        self.assertEqual(note.data, {"order": self.order.id, "action": "rebook"})
        self.assertFalse(self.customer.charges.exists())  # no fee

    def test_closed_day_has_no_slots_and_cannot_be_booked(self):
        nasr = Zone.objects.get(name="مدينة نصر")
        with frozen_now(BEFORE):
            close_day(WED, nasr, "مطر", self.manager)
            r = available_slots(self.customer, self.address.id, [{"car": self.car.id, "services": sid("exterior-wash")}])
            wed = next(d for d in r["days"] if d["date"] == WED.isoformat())
            self.assertEqual(wed["slots"], [])
            with self.assertRaises(BusinessError):
                create_order(self.customer, self.address.id, [{"car": self.car.id, "services": sid("exterior-wash")}],
                             cairo(WED, 16))

    def test_close_all_zones_and_reopen(self):
        c = APIClient()
        c.force_authenticate(self.manager)
        with frozen_now(BEFORE):
            r = c.post("/api/manage/closed-days/", {"date": WED.isoformat(), "zone": None, "reason": "عاصفة"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["cancelled_orders"], 1)
        self.assertEqual(c.post("/api/manage/closed-days/", {"date": WED.isoformat(), "reason": ""}, format="json").status_code, 400)
        cid = r.json()["id"]
        self.assertEqual(c.delete(f"/api/manage/closed-days/{cid}/").status_code, 204)  # reopen for new bookings
        with frozen_now(BEFORE):
            r = available_slots(self.customer, self.address.id, [{"car": self.car.id, "services": sid("exterior-wash")}])
        wed = next(d for d in r["days"] if d["date"] == WED.isoformat())
        self.assertTrue(wed["slots"])
