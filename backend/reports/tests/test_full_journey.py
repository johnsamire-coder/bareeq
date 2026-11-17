"""The whole phase-1 journey through the API, the way the app uses it:
customer signs up -> car + address -> quote -> slots -> booking -> coupon ->
wallet + InstaPay -> manager approves -> technician job with 8 photos ->
invoice -> rating -> technician closing -> manager confirms -> reports."""
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import TermsVersion, User
from cars.models import CarBrand, CarColor, CarModel
from orders.tests.helpers import CITY_STARS, WED, cairo, frozen_now, jpeg_bytes, make_technician
from payments.tests.helpers import MEDIA
from services.models import Service

T = cairo(WED, 9) - timedelta(days=1)  # Tuesday 9:00, booking for Wednesday


def img():
    return SimpleUploadedFile("p.jpg", jpeg_bytes(size=(400, 300)), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class FullJourneyTests(TestCase):
    def test_full_phase_one_journey(self):
        tech = make_technician("01100000001")
        User.objects.create_user("01000000001", "المدير", role="manager")
        cust, techc, mgr = APIClient(), APIClient(), APIClient()

        def login(client, phone, signup=None):
            with mock.patch("accounts.otp_senders.ConsoleOtpSender.send") as send:
                self.assertEqual(client.post("/api/auth/otp/request/", {"phone": phone}, format="json").status_code, 200)
                code = send.call_args[0][1]
            r = client.post("/api/auth/otp/verify/", {"phone": phone, "code": code, **(signup or {})}, format="json")
            self.assertEqual(r.status_code, 200, r.content)
            client.credentials(HTTP_AUTHORIZATION="Token " + r.json()["token"])
            return r.json()

        with frozen_now(T):
            # 1. Customer signs up (terms accepted) and adds a car and an address.
            me = login(cust, "01012345678", {"full_name": "سارة محمد", "terms_version": TermsVersion.current().version})
            self.assertTrue(me["is_new"])
            m = CarModel.objects.get(brand__name_en="Toyota", name="Corolla")
            car = cust.post("/api/my-cars/", {"brand": m.brand_id, "model": m.id, "year": 2022,
                                              "color": CarColor.objects.first().id, "parking": "closed_garage"}, format="json").json()
            addr = cust.post("/api/my-addresses/", {"label": "البيت", "lat": CITY_STARS[0], "lng": CITY_STARS[1],
                                                     "building": "5"}, format="json").json()
            self.assertEqual(addr["zone"]["name"], "مدينة نصر")

            # 2. Quote and slots: basic bundle on a sedan = 243 EGP, 85 minutes.
            svc = [Service.objects.get(code=c).id for c in ("exterior-wash", "interior-wash")]
            q = cust.post("/api/services/quote/", {"address": addr["id"], "car": car["id"], "services": svc}, format="json").json()
            self.assertEqual((q["total"], q["total_minutes"]), (24300, 85))
            items = [{"car": car["id"], "services": svc}]
            slots = cust.post("/api/booking/slots/", {"address": addr["id"], "items": items}, format="json").json()
            wed = next(d for d in slots["days"] if d["date"] == WED.isoformat())
            start = wed["slots"][2]["start"]  # 10:00

            # 3. Manager makes a launch coupon and gives the customer 30 EGP.
            login(mgr, "01000000001")
            mgr.post("/api/manage/coupons/", {"code": "BAREEQ10", "kind": "percent", "value": 10,
                                              "expires_at": (T + timedelta(days=30)).isoformat()}, format="json")
            mgr.post("/api/manage/wallets/credit/", {"customer": me["user"]["id"], "amount": 3000, "note": "هدية افتتاح"}, format="json")

            # 4. Book, coupon, pay 30 from the wallet + the rest by InstaPay.
            order = cust.post("/api/orders/", {"address": addr["id"], "items": items, "start": start}, format="json").json()
            oid = order["id"]
            o = cust.post(f"/api/orders/{oid}/coupon/", {"code": "bareeq10"}, format="json").json()
            self.assertEqual(o["amount_due"], 21900)  # 243 - 24 (10% = 24.30 -> 24)
            o = cust.post(f"/api/orders/{oid}/confirm/", {"payment_method": "instapay", "wallet_amount": 3000, "proof": img()},
                          format="multipart").json()
            self.assertEqual((o["status"], o["wallet_used"], o["amount_to_collect"]), ("confirmed", 3000, 0))

            # 5. Manager approves the transfer from the inbox.
            inbox = mgr.get("/api/manage/inbox/").json()
            self.assertEqual(inbox["instapay_to_review"], 1)
            pay = mgr.get("/api/manage/payments/", {"status": "pending_review"}).json()[0]
            self.assertEqual(pay["amount"], 18900)
            mgr.post(f"/api/manage/payments/{pay['id']}/approve/")

        # 6. Technician's day.
        login(techc, "01100000001")
        base = f"/api/technician/jobs/{oid}"
        start_dt = cairo(WED, 10)
        with frozen_now(start_dt - timedelta(minutes=30)):
            self.assertEqual([j["id"] for j in techc.get("/api/technician/jobs/").json()], [oid])
            techc.post(f"{base}/on-the-way/")
        with frozen_now(start_dt):
            techc.post(f"{base}/arrived/", {"lat": CITY_STARS[0], "lng": CITY_STARS[1]}, format="json")
            for side in ("front", "back", "left", "right"):
                r = techc.post(f"{base}/photos/", {"stage": "before", "side": side, "image": img(), "captured_at": start_dt.isoformat(),
                                                   "lat": CITY_STARS[0], "lng": CITY_STARS[1]}, format="multipart")
                self.assertEqual(r.status_code, 201, r.content)
            self.assertEqual(techc.post(f"{base}/start/").json()["status"], "in_progress")
        end = start_dt + timedelta(minutes=85)
        with frozen_now(end):
            for side in ("front", "back", "left", "right"):
                techc.post(f"{base}/photos/", {"stage": "after", "side": side, "image": img(), "captured_at": end.isoformat(),
                                               "lat": CITY_STARS[0], "lng": CITY_STARS[1]}, format="multipart")
            self.assertEqual(techc.post(f"{base}/complete/").json()["status"], "completed")  # nothing to collect

            # 7. Customer: invoice, notifications, rating.
            inv = cust.get(f"/api/orders/{oid}/invoice/").json()
            self.assertEqual(inv["number"], "BR-2026-000001")
            self.assertEqual((inv["total"], inv["wallet_amount"], inv["instapay_amount"], inv["cash_amount"]), (21900, 3000, 18900, 0))
            kinds = [n["kind"] for n in cust.get("/api/notifications/").json()["results"]]
            for k in ("welcome", "wallet_credit", "booking_confirmed", "technician_on_the_way", "job_done"):
                self.assertIn(k, kinds)
            r = cust.post(f"/api/orders/{oid}/rating/", {"stars": 5, "tags": [], "comment": "ممتاز"}, format="json")
            self.assertEqual(r.status_code, 201)

            # 8. Technician closing (no cash today) and manager confirms.
            c = techc.post("/api/technician/closing/", {"date": WED.isoformat(), "cash_handed": 0}, format="json").json()
            self.assertEqual(c["difference"], 0)
            mgr.post(f"/api/manage/daily-closings/{c['id']}/confirm/")

            # 9. Reports show it.
            # From the booking day (the rating is stamped with the real clock) to Wednesday.
            rep = mgr.get("/api/manage/reports/", {"from": T.date().isoformat(), "to": WED.isoformat()}).json()
            t = rep["totals"]
            self.assertEqual((t["orders"], t["revenue"], t["collected"], t["wallet"], t["uncollected"]), (1, 21900, 18900, 3000, 0))
            self.assertEqual(rep["ratings"]["average"], 5.0)
            self.assertEqual(rep["customers"]["first_time"], 1)
            self.assertEqual(rep["job_times"], [])  # two services: not used for single-service timing
            profile = mgr.get(f"/api/manage/customers/{me['user']['id']}/").json()
            self.assertEqual((profile["stats"]["completed_orders"], profile["stats"]["total_paid"]), (1, 21900))
