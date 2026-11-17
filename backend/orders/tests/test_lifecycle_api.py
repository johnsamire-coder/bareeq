import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from orders.lifecycle import cancel_by_customer
from orders.models import CustomerCharge

from .helpers import CITY_STARS, WED, book_confirmed, cairo, frozen_now, jpeg_bytes, make_customer, make_technician

SIDES = ["front", "back", "left", "right"]


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TechnicianApiTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.order = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))
        self.client = APIClient()
        self.client.force_authenticate(self.tech)
        self.base = f"/api/technician/jobs/{self.order.id}"

    def upload(self, stage, side, when):
        return self.client.post(f"{self.base}/photos/", {
            "stage": stage, "side": side, "captured_at": when.isoformat(),
            "lat": CITY_STARS[0], "lng": CITY_STARS[1], "accuracy_m": 6,
            "image": SimpleUploadedFile("p.jpg", jpeg_bytes(), content_type="image/jpeg"),
        }, format="multipart")

    def test_day_list_and_full_flow(self):
        with frozen_now(cairo(WED, 8)):
            jobs = self.client.get("/api/technician/jobs/").json()
        self.assertEqual([j["id"] for j in jobs], [self.order.id])
        self.assertEqual(jobs[0]["customer_phone"], "+201012345678")
        with frozen_now(cairo(WED, 13, 40)):
            self.assertEqual(self.client.post(f"{self.base}/on-the-way/").json()["status"], "on_the_way")
        with frozen_now(cairo(WED, 14)):
            self.assertEqual(self.client.post(f"{self.base}/arrived/", {"lat": "30.0729", "lng": "31.3456"},
                                              format="json").json()["status"], "arrived")
            r = self.client.post(f"{self.base}/start/")
            self.assertEqual(r.json()["code"], "before_photos_missing")
            for side in SIDES:
                r = self.upload("before", side, cairo(WED, 14))
                self.assertEqual(r.status_code, 201, r.content)
            self.assertEqual(self.client.post(f"{self.base}/start/").json()["status"], "in_progress")
        with frozen_now(cairo(WED, 14, 45)):
            for side in SIDES:
                self.upload("after", side, cairo(WED, 14, 45))
            r = self.client.post(f"{self.base}/complete/")
            self.assertEqual(r.json()["status"], "completed")
        photos = self.client.get(f"{self.base}/photos/").json()
        self.assertEqual(len(photos), 8)

        # Who can open a photo file.
        url = photos[0]["url"]
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_authenticate(self.customer)
        r = self.client.get(url)
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "image/jpeg"))
        self.assertEqual(len(self.client.get(f"/api/orders/{self.order.id}/photos/").json()), 8)
        stranger, _, _ = make_customer("01012345670")
        self.client.force_authenticate(stranger)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, 401)

    def test_other_technician_cannot_see_job(self):
        other = make_technician("01100000002")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(f"{self.base}/on-the-way/").status_code, 404)

    def test_car_not_found_api(self):
        with frozen_now(cairo(WED, 13, 40)):
            self.client.post(f"{self.base}/on-the-way/")
        with frozen_now(cairo(WED, 14)):
            self.client.post(f"{self.base}/arrived/")
            self.client.post(f"{self.base}/called-customer/")
        with frozen_now(cairo(WED, 14, 16)):
            r = self.client.post(f"{self.base}/car-not-found/", {"lat": "30.0729", "lng": "31.3456"}, format="json")
        self.assertEqual(r.json()["status"], "car_not_found")
        self.client.force_authenticate(self.customer)
        charges = self.client.get("/api/my-charges/").json()
        self.assertEqual([(c["kind"], c["amount"]) for c in charges], [("car_not_found", 5000)])


class CustomerAndManagerApiTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def test_customer_reschedule_and_cancel(self):
        with frozen_now(cairo(WED, 8)):
            r = self.client.post(f"/api/orders/{self.order.id}/reschedule/", {"start": cairo(WED, 16).isoformat()}, format="json")
            self.assertEqual(r.status_code, 200, r.content)
            self.assertTrue(r.json()["scheduled_start"].startswith("2026-11-18T16:00"))
        with frozen_now(cairo(WED, 15)):
            r = self.client.post(f"/api/orders/{self.order.id}/cancel/", {"reason": "ظرف"}, format="json")
        self.assertEqual(r.json()["status"], "cancelled_by_customer")
        self.assertEqual(self.client.get("/api/my-charges/").json()[0]["amount"], 5000)

    def test_manager_waives_with_reason(self):
        with frozen_now(cairo(WED, 13)):
            cancel_by_customer(self.order)
        charge = CustomerCharge.objects.get()
        self.client.force_authenticate(self.manager)
        self.assertEqual(len(self.client.get("/api/manage/customer-charges/", {"open": 1}).json()), 1)
        r = self.client.post(f"/api/manage/customer-charges/{charge.id}/waive/", {"reason": ""}, format="json")
        self.assertEqual(r.json()["code"], "reason_required")
        r = self.client.post(f"/api/manage/customer-charges/{charge.id}/waive/", {"reason": "عميل مميز"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["waived_by"], self.manager.id)
        self.assertEqual(self.client.get("/api/manage/customer-charges/", {"open": 1}).json(), [])
        # Customers cannot waive.
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post(f"/api/manage/customer-charges/{charge.id}/waive/", {"reason": "x"}).status_code, 403)

    def test_manager_cancels_for_company(self):
        self.client.force_authenticate(self.manager)
        r = self.client.post(f"/api/manage/orders/{self.order.id}/cancel/", {"reason": "عاصفة ترابية"}, format="json")
        self.assertEqual(r.json()["status"], "cancelled_by_company")
        self.assertFalse(CustomerCharge.objects.exists())
