"""The whole phase-3 journey through the API, the way the app uses it:
a customer pays a normal order by card -> cancels -> money back to the card;
then subscribes (plan price for her car and area) -> picks a weekly time ->
pays the month by card on the payment page -> four visits confirmed -> the
technician does the first -> the manager sees subscribers and the money."""
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from orders.lifecycle import complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments.models import Payment
from payments.tests.helpers import MEDIA, work_until_done_photos
from services.models import Service
from subscriptions.models import SubscriptionPlan

NOW = cairo(WED, 9) - timedelta(days=1)


@override_settings(MEDIA_ROOT=MEDIA, PAYMENT_GATEWAY="fake")
class PhaseThreeJourneyTests(TestCase):
    def test_full_phase_three_journey(self):
        tech = make_technician("01100000001")
        manager = User.objects.create_user("01000000001", "المدير", role="manager")
        customer, car, address = make_customer()
        api, mgr, page = APIClient(), APIClient(), APIClient()
        api.force_authenticate(customer)
        mgr.force_authenticate(manager)
        svc = [Service.objects.get(code=c).id for c in ("exterior-wash", "interior-wash")]

        with frozen_now(NOW):
            # 1. A normal order paid by card, then cancelled: the money goes back to the card.
            info = api.get("/api/payment-info/").json()
            self.assertTrue(info["card_payment_enabled"])
            o = api.post("/api/orders/", {"address": address.id, "items": [{"car": car.id, "services": svc}],
                                          "start": cairo(WED, 15).isoformat()}, format="json").json()
            r = api.post(f"/api/orders/{o['id']}/pay-online/", {}, format="json").json()
            self.assertIn("صفحة دفع تجريبية", page.get(f"/api/pay/fake/{r['ref']}/").content.decode())
            page.post(f"/api/pay/fake/{r['ref']}/", {"action": "pay"})
            self.assertEqual(api.get(f"/api/pay/{r['ref']}/").json()["status"], "paid")
            self.assertEqual(api.get(f"/api/orders/{o['id']}/").json()["payment_method"], "card")
            api.post(f"/api/orders/{o['id']}/cancel/", {"reason": ""}, format="json")
            self.assertEqual(api.get(f"/api/orders/{o['id']}/").json()["card_refund_due"], 24300)
            self.assertEqual(api.post(f"/api/orders/{o['id']}/refund-to-card/").json(), {"refunded": 24300})

            # 2. Subscribe: 4 washes a month, 15% off -> 826 EGP for a sedan in Nasr City.
            plan = api.get("/api/subscription-plans/", {"car": car.id, "address": address.id}).json()[0]
            self.assertEqual((plan["price"], plan["washes_per_month"]), (82600, 4))
            sub = api.post("/api/my-subscriptions/", {"plan": plan["id"], "car": car.id, "address": address.id,
                                                      "start": cairo(WED, 10).isoformat()}, format="json").json()
            period = sub["current"]
            self.assertEqual([v["amount_due"] for v in period["visits"]], [20800, 20600, 20600, 20600])

            # 3. Pay the month by card.
            r = api.post(f"/api/subscription-periods/{period['id']}/pay-online/", {}, format="json").json()
            self.assertEqual(r["amount"], 82600)
            page.post(f"/api/pay/fake/{r['ref']}/", {"action": "pay"})
            mine = api.get("/api/my-subscriptions/").json()[0]
            self.assertEqual(mine["current"]["status"], "paid")
            self.assertEqual({v["status"] for v in mine["current"]["visits"]}, {"confirmed"})

        # 4. The technician does the first visit (nothing to collect).
        first = SubscriptionPlan.objects.get().subscriptions.get().periods.get().visits.order_by("scheduled_start")[0]
        end = work_until_done_photos(first, tech, cairo(WED, 10))
        with frozen_now(end):
            first.refresh_from_db()
            self.assertEqual(first.amount_to_collect, 0)
            complete_job(first, tech)
            inv = api.get(f"/api/orders/{first.id}/invoice/").json()
            self.assertEqual((inv["total"], inv["card_amount"]), (20800, 20800))

            # 5. The manager sees it.
            rep = mgr.get("/api/manage/reports/subscriptions/", {"month": "2026-11"}).json()
            self.assertEqual((rep["active_subscriptions"], rep["revenue"], rep["discount_given"]), (1, 82600, 14600))
            self.assertEqual(mgr.get("/api/manage/subscriptions/").json()[0]["customer_name"], "عميل")
        self.assertEqual(Payment.objects.filter(status="refunded", method="card").count(), 1)
