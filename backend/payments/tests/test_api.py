from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments import wallet
from payments.models import Invoice, Material, Payment

from .helpers import MEDIA, book, proof, work_until_done_photos

START = cairo(WED, 10)
BEFORE = START - timedelta(days=1)


@override_settings(MEDIA_ROOT=MEDIA)
class PaymentsApiTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)
        self.c = APIClient()

    def as_(self, user):
        self.c.force_authenticate(user)
        return self.c

    def test_instapay_full_cycle_with_wallet(self):
        # Manager gives 100 EGP; customer pays 100 from wallet + 143 by InstaPay.
        r = self.as_(self.manager).post("/api/manage/wallets/credit/", {"customer": self.customer.id, "amount": 10000,
                                                                       "note": "تعويض"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        info = self.as_(self.customer).get("/api/payment-info/").json()
        self.assertEqual(info["wallet_balance"], 10000)
        self.assertIn("[مؤقت]", info["instapay_details"])
        with frozen_now(BEFORE):
            r = self.c.post(f"/api/orders/{self.order.id}/confirm/",
                            {"payment_method": "instapay", "wallet_amount": 10000, "proof": proof()}, format="multipart")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()["wallet_used"], r.json()["amount_to_collect"]), (10000, 0))
        self.assertEqual(self.c.get("/api/my-wallet/").json()["balance"], 0)

        pending = self.as_(self.manager).get("/api/manage/payments/", {"status": "pending_review"}).json()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["amount"], 14300)
        self.assertEqual(self.c.get(pending[0]["proof_url"]).status_code, 200)
        self.assertEqual(self.as_(self.tech).get(pending[0]["proof_url"]).status_code, 403)
        r = self.as_(self.manager).post(f"/api/manage/payments/{pending[0]['id']}/approve/")
        self.assertEqual(r.json()["status"], "confirmed")

        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            r = self.as_(self.tech).post(f"/api/technician/jobs/{self.order.id}/complete/")
        self.assertEqual(r.json()["status"], "completed", r.content)
        inv = self.as_(self.customer).get(f"/api/orders/{self.order.id}/invoice/").json()
        self.assertEqual(inv["number"], "BR-2026-000001")
        self.assertEqual((inv["wallet_amount"], inv["instapay_amount"], inv["cash_amount"]), (10000, 14300, 0))
        self.assertEqual(len(self.c.get("/api/my-invoices/").json()), 1)

    def test_invoice_cancel_api(self):
        with frozen_now(BEFORE):
            self.as_(self.customer).post(f"/api/orders/{self.order.id}/confirm/", {"payment_method": "cash"}, format="json")
        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            self.as_(self.tech).post(f"/api/technician/jobs/{self.order.id}/complete/", {"cash_collected": 24300}, format="json")
        inv = Invoice.objects.get()
        r = self.as_(self.manager).post(f"/api/manage/invoices/{inv.id}/cancel/", {"reason": ""}, format="json")
        self.assertEqual(r.json()["code"], "reason_required")
        r = self.c.post(f"/api/manage/invoices/{inv.id}/cancel/", {"reason": "غلط في البيانات"}, format="json")
        self.assertEqual(r.json()["status"], "cancelled")
        self.assertEqual(self.c.delete(f"/api/manage/invoices/{inv.id}/").status_code, 405)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_materials_and_closing_api(self):
        m = self.as_(self.manager).post("/api/manage/materials/", {"name": "شامبو", "unit": "liter", "unit_cost": 8000},
                                        format="json").json()
        with frozen_now(BEFORE):
            self.as_(self.customer).post(f"/api/orders/{self.order.id}/confirm/", {"payment_method": "cash"}, format="json")
        end = work_until_done_photos(self.order, self.tech, START)
        t = self.as_(self.tech)
        self.assertEqual([x["name"] for x in t.get("/api/technician/materials/").json()], ["شامبو"])
        r = t.post(f"/api/technician/jobs/{self.order.id}/materials/", {"items": [{"material": m["id"], "quantity": "0.25"}]},
                   format="json")
        self.assertEqual(r.json()["materials_cost"], 2000)
        with frozen_now(end):
            t.post(f"/api/technician/jobs/{self.order.id}/complete/", {"cash_collected": 24300}, format="json")
        s = t.get("/api/technician/closing/", {"date": WED.isoformat()}).json()
        self.assertEqual((s["cash_collected"], s["materials_cost"]), (24300, 2000))
        r = t.post("/api/technician/closing/", {"date": WED.isoformat(), "cash_handed": 24300}, format="json")
        self.assertEqual(r.json()["difference"], 0)
        closings = self.as_(self.manager).get("/api/manage/daily-closings/", {"status": "submitted"}).json()
        r = self.c.post(f"/api/manage/daily-closings/{closings[0]['id']}/confirm/")
        self.assertEqual(r.json()["status"], "confirmed")
        money = self.c.get(f"/api/manage/orders/{self.order.id}/money/").json()
        self.assertEqual((money["materials_cost"], money["margin"]), (2000, 22300))

    def test_role_checks(self):
        self.assertEqual(self.as_(self.customer).get("/api/manage/payments/").status_code, 403)
        self.assertEqual(self.c.post("/api/manage/wallets/credit/", {}).status_code, 403)
        self.assertEqual(self.c.get("/api/technician/closing/").status_code, 403)
        self.assertEqual(self.as_(self.tech).get("/api/my-wallet/").status_code, 403)


class AdminPagesTests(TestCase):
    def test_pages_open(self):
        admin = User.objects.create_superuser("01000000009", "Admin", password="pw-For-Test-1")
        self.client.force_login(admin)
        m = Material.objects.create(name="واكس", unit="box", unit_cost=12000)
        for url in ("/admin/payments/material/", f"/admin/payments/material/{m.id}/change/",
                    "/admin/payments/material/add/", "/admin/payments/invoice/", "/admin/payments/walletentry/",
                    "/admin/payments/payment/", "/admin/payments/dailyclosing/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get(f"/admin/payments/material/{m.id}/change/"), 'value="120')
        r = self.client.post(f"/admin/payments/material/{m.id}/change/",
                             {"name": "واكس", "unit": "box", "sort_order": 0, "is_active": "on", "price_pounds": "135.5"})
        self.assertEqual(r.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.unit_cost, 13550)
