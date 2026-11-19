"""The whole phase-2 journey through the API, the way the app uses it:
an existing customer shares her code -> a friend signs up with it -> his first
order gets the invite discount -> paid by InstaPay, manager approves -> the job
is done -> cashback for him, invite credit for her -> wash card counts ->
the manager sees it in the wallet report."""
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import TermsVersion, User
from cars.models import CarColor, CarModel
from core.models import Setting
from orders.tests.helpers import CITY_STARS, WED, cairo, frozen_now, jpeg_bytes, make_customer, make_technician
from payments.tests.helpers import MEDIA
from services.models import Service

T = cairo(WED, 9) - timedelta(days=1)
FRIEND_HOME = (30.0600, 31.3300)


def img():
    return SimpleUploadedFile("p.jpg", jpeg_bytes(size=(400, 300)), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class PhaseTwoJourneyTests(TestCase):
    def test_full_phase_two_journey(self):
        make_technician("01100000001")
        User.objects.create_user("01000000001", "المدير", role="manager")
        Setting.objects.filter(key="cashback-enabled").update(value=True)  # the manager switched it on
        sara, _, _ = make_customer("01012345678")
        sara_c, friend, techc, mgr = APIClient(), APIClient(), APIClient(), APIClient()
        sara_c.force_authenticate(sara)

        def login(client, phone, signup=None, device="phone-friend"):
            with mock.patch("accounts.otp_senders.ConsoleOtpSender.send") as send:
                client.post("/api/auth/otp/request/", {"phone": phone, "device_id": device}, format="json")
                code = send.call_args[0][1]
            r = client.post("/api/auth/otp/verify/", {"phone": phone, "code": code, **(signup or {})}, format="json")
            self.assertEqual(r.status_code, 200, r.content)
            client.credentials(HTTP_AUTHORIZATION="Token " + r.json()["token"])
            return r.json()

        with frozen_now(T):
            # 1. Sara opens «مكافآتي» and shares her code.
            rewards = sara_c.get("/api/my-rewards/").json()
            code = rewards["referral"]["code"]
            self.assertEqual(rewards["referral"]["invited"], 0)

            # 2. Her friend signs up with it, adds a car and an address.
            me = login(friend, "01055500001", {"full_name": "كريم", "terms_version": TermsVersion.current().version,
                                               "referral_code": code.lower()})
            m = CarModel.objects.get(brand__name_en="Toyota", name="Corolla")
            car = friend.post("/api/my-cars/", {"brand": m.brand_id, "model": m.id, "year": 2022,
                                                "color": CarColor.objects.first().id, "parking": "closed_garage"},
                              format="json").json()
            addr = friend.post("/api/my-addresses/", {"label": "البيت", "lat": FRIEND_HOME[0], "lng": FRIEND_HOME[1],
                                                      "building": "5"}, format="json").json()

            # 3. His first order: basic bundle 243 - invite discount 50 = 193.
            svc = [Service.objects.get(code=c).id for c in ("exterior-wash", "interior-wash")]
            items = [{"car": car["id"], "services": svc}]
            start = cairo(WED, 10).isoformat()
            o = friend.post("/api/orders/", {"address": addr["id"], "items": items, "start": start}, format="json").json()
            self.assertEqual((o["extra_discount_kind"], o["extra_discount_label"], o["amount_due"], o["cashback_percent"]),
                             ("referral", "خصم أول طلب (دعوة)", 19300, 5))
            oid = o["id"]
            o = friend.post(f"/api/orders/{oid}/confirm/", {"payment_method": "instapay", "proof": img()},
                            format="multipart").json()
            self.assertEqual(o["status"], "confirmed")
            login(mgr, "01000000001", device="manager-phone")
            pay = mgr.get("/api/manage/payments/", {"status": "pending_review"}).json()[0]
            mgr.post(f"/api/manage/payments/{pay['id']}/approve/")

        # 4. The technician does the job.
        login(techc, "01100000001", device="tech-phone")
        base = f"/api/technician/jobs/{oid}"
        s = cairo(WED, 10)
        with frozen_now(s - timedelta(minutes=30)):
            techc.post(f"{base}/on-the-way/")
        with frozen_now(s):
            techc.post(f"{base}/arrived/", {"lat": FRIEND_HOME[0], "lng": FRIEND_HOME[1]}, format="json")
            for side in ("front", "back", "left", "right"):
                techc.post(f"{base}/photos/", {"stage": "before", "side": side, "image": img(),
                                               "captured_at": s.isoformat(), "lat": FRIEND_HOME[0],
                                               "lng": FRIEND_HOME[1]}, format="multipart")
            techc.post(f"{base}/start/")
        end = s + timedelta(minutes=85)
        with frozen_now(end):
            for side in ("front", "back", "left", "right"):
                techc.post(f"{base}/photos/", {"stage": "after", "side": side, "image": img(),
                                               "captured_at": end.isoformat(), "lat": FRIEND_HOME[0],
                                               "lng": FRIEND_HOME[1]}, format="multipart")
            self.assertEqual(techc.post(f"{base}/complete/").json()["status"], "completed")

            # 5. Rewards: 5% cashback of 193 = 9 for him, 50 invite credit for Sara.
            o = friend.get(f"/api/orders/{oid}/").json()
            self.assertEqual(o["cashback_amount"], 900)
            inv = friend.get(f"/api/orders/{oid}/invoice/").json()
            self.assertEqual(inv["lines"]["extra_discount"]["kind"], "referral")
            mine = friend.get("/api/my-rewards/").json()
            self.assertEqual((mine["wallet_balance"], mine["cashback"]["earned"], mine["wash_card"]["done"]), (900, 900, 1))
            rewards = sara_c.get("/api/my-rewards/").json()
            self.assertEqual((rewards["wallet_balance"], rewards["referral"]["invited"],
                              rewards["referral"]["credited"], rewards["referral"]["earned"]), (5000, 1, 1, 5000))
            kinds = [n["title"] for n in sara_c.get("/api/notifications/").json()["results"]]
            self.assertIn("صاحبك جرّب بريق", kinds)

            # 6. The manager's wallet report for the month.
            r = mgr.get("/api/manage/reports/wallet/", {"month": "2026-11"}).json()
            credited = {c["kind"]: c["amount"] for c in r["credited"]}
            self.assertEqual((credited["cashback"], credited["referral"], r["liability_now"]), (900, 5000, 5900))
