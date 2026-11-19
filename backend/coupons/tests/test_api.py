from datetime import timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import TermsVersion, User
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments.tests.helpers import book

START = cairo(WED, 10)


class CouponApiTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.c = APIClient()

    def test_manager_creates_customer_applies(self):
        self.c.force_authenticate(self.manager)
        r = self.c.post("/api/manage/coupons/", {"code": "launch20", "kind": "percent", "value": 20,
                                                  "expires_at": (START + timedelta(days=30)).isoformat(),
                                                  "max_uses_total": 100, "max_uses_per_customer": 1}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["code"], "LAUNCH20")
        self.assertEqual(self.c.post("/api/manage/coupons/", {"code": "Launch20", "kind": "amount", "value": 5000,
                                                               "expires_at": START.isoformat()}, format="json").status_code, 400)
        self.assertEqual(self.c.post("/api/manage/coupons/", {"code": "BAD", "kind": "percent", "value": 120,
                                                               "expires_at": START.isoformat()}, format="json").status_code, 400)
        order = book(self.customer, self.car, self.address, START)
        self.c.force_authenticate(self.customer)
        with frozen_now(START - timedelta(days=1)):
            r = self.c.post(f"/api/orders/{order.id}/coupon/", {"code": "LAUNCH20"}, format="json")
            self.assertEqual(r.status_code, 200, r.content)
            self.assertEqual((r.json()["coupon_code"], r.json()["extra_discount"], r.json()["amount_due"]), ("LAUNCH20", 4800, 19500))
            r = self.c.post(f"/api/orders/{order.id}/coupon/", {"code": "WRONG"}, format="json")
            self.assertEqual(r.json()["code"], "coupon_invalid")
            r = self.c.delete(f"/api/orders/{order.id}/coupon/")
            self.assertEqual(r.json()["amount_due"], 24300)
        self.assertEqual(self.c.get("/api/manage/coupons/").status_code, 403)


class TermsAndListsApiTests(TestCase):
    def test_publish_terms_and_heard_about(self):
        manager = User.objects.create_user("01000000001", "Boss", role="manager")
        c = APIClient()
        c.force_authenticate(manager)
        rows = c.get("/api/manage/terms/").json()
        self.assertEqual(rows[0]["version"], 4)
        self.assertEqual(c.post("/api/manage/terms/", {"text": rows[0]["text"]}, format="json").json()["code"], "no_change")
        r = c.post("/api/manage/terms/", {"text": rows[0]["text"] + "\n- بند جديد للتجربة."}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(TermsVersion.current().version, 5)
        self.assertEqual(TermsVersion.current().created_by, manager)
        r = c.post("/api/manage/heard-about-options/", {"label": "إعلان على الإنستجرام", "sort_order": 9}, format="json")
        self.assertEqual(r.status_code, 201)
        c.force_authenticate(User.objects.create_user("01012345678", "c"))
        self.assertEqual(c.get("/api/manage/terms/").status_code, 403)
