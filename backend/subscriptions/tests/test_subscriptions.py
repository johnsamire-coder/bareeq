"""Monthly subscription (phase 3, rules agreed with John 19 Nov 2026)."""
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from core.errors import BusinessError
from core.models import Setting
from coupons.models import Coupon
from coupons.service import apply_coupon
from feedback.service import close_day
from notifications.models import Notification
from orders.booking import expire_holds
from orders.lifecycle import cancel_by_customer, complete_job, reschedule
from orders.models import Order
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments import online, wallet
from payments.gateway.fake import sign
from payments.models import Payment, WalletEntry
from payments.payments import review_instapay
from payments.tests.helpers import MEDIA, book, proof, work_until_done_photos
from subscriptions import service
from subscriptions.models import SubscriptionPeriod, SubscriptionPlan

START = cairo(WED, 10)
NOW = START - timedelta(days=1)


def paid_callback(p):
    return {"ref": p.ref, "paid": "1", "amount": p.amount, "txn_id": "T", "signature": sign(p.ref, True, p.amount, "T")}


@override_settings(MEDIA_ROOT=MEDIA, PAYMENT_GATEWAY="fake")
class SubscriptionTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.plan = SubscriptionPlan.objects.get()  # seeded: 4 washes, exterior + interior, 15% off

    def subscribe(self, start=START):
        with frozen_now(NOW):
            return service.subscribe(self.customer, self.plan.id, self.car.id, self.address.id, start)

    def visits(self, period):
        return list(period.visits.order_by("scheduled_start"))

    def pay_card(self, period, wallet_amount=0):
        with frozen_now(NOW):
            p = service.start_online(period, self.customer, wallet_amount)
            online.handle_callback("fake", paid_callback(p))
        period.refresh_from_db()
        return period

    def test_price_and_four_weekly_visits(self):
        price, normal = service.plan_price(self.plan, self.car, self.address)
        self.assertEqual((normal, price), (97200, 82600))  # 4 x 243 = 972, -15% = 826.20 -> 826
        sub = self.subscribe()
        period = sub.periods.get()
        v = self.visits(period)
        self.assertEqual([o.scheduled_start for o in v], [START + timedelta(days=7 * i) for i in range(4)])
        self.assertEqual([o.amount_due for o in v], [20800, 20600, 20600, 20600])  # whole pounds, = 826
        self.assertEqual({o.extra_discount_kind for o in v}, {"subscription"})
        self.assertEqual((period.start_date, period.end_date), (WED, WED + timedelta(days=27)))
        self.assertEqual({o.technician for o in v}, {self.tech})
        self.assertEqual((sub.weekday, sub.start_time.hour), (START.weekday(), 10))

    def test_pay_by_card_confirms_the_month(self):
        wallet.credit(self.customer, 20000, "manual", created_by=self.manager, note="هدية")
        period = self.pay_card(self.subscribe().periods.get(), wallet_amount=10000)
        self.assertEqual(period.status, "paid")
        v = self.visits(period)
        self.assertEqual({o.status for o in v}, {"confirmed"})
        self.assertEqual(sum(o.wallet_used for o in v), 10000)
        money = sum(p.amount for p in Payment.objects.filter(order__in=v, method="card", status="confirmed"))
        self.assertEqual(money + 10000, 82600)
        self.assertEqual(sum(o.amount_to_collect for o in v), 0)
        self.assertTrue(Notification.objects.filter(user=self.customer, kind="subscription").exists())

    def test_instapay_one_review_for_the_month(self):
        period = self.subscribe().periods.get()
        with frozen_now(NOW):
            service.pay_instapay(period, self.customer, proof())
        pays = Payment.objects.filter(order__subscription_period=period)
        self.assertEqual((pays.count(), {p.status for p in pays}), (4, {"pending_review"}))
        review_instapay(pays.first(), self.manager, approve=True)
        self.assertEqual({p.status for p in Payment.objects.filter(order__subscription_period=period)}, {"confirmed"})

    def test_no_cash(self):
        period = self.subscribe().periods.get()
        from payments.payments import confirm_with_payment

        # a visit cannot be confirmed alone with cash: the month is paid together
        with frozen_now(NOW), self.assertRaises(BusinessError) as e:
            confirm_with_payment(self.visits(period)[0], "cash")
        self.assertEqual(e.exception.detail["code"], "pay_the_month")

    def test_busy_week_is_reported(self):
        other, car, address = make_customer("01012300000")
        b = book(other, car, address, START + timedelta(days=14))
        with frozen_now(NOW):
            from payments.payments import confirm_with_payment
            confirm_with_payment(b, "cash")
        with self.assertRaises(BusinessError) as e:
            self.subscribe()
        self.assertEqual(e.exception.detail["code"], "subscription_slots_taken")
        self.assertIn((WED + timedelta(days=14)).strftime("%d/%m"), str(e.exception.detail["detail"]))
        self.assertFalse(SubscriptionPeriod.objects.exists())  # nothing half-booked

    def test_unpaid_month_expires(self):
        period = self.subscribe().periods.get()
        with frozen_now(NOW + timedelta(hours=1)):
            expire_holds()
            service.expire_unpaid()
        period.refresh_from_db()
        self.assertEqual(period.status, "expired")

    def test_visit_rules(self):
        period = self.pay_card(self.subscribe().periods.get())
        v = self.visits(period)
        # no coupons
        Coupon.objects.create(code="X", kind="amount", value=1000, expires_at=START + timedelta(days=60),
                              max_uses_total=10, max_uses_per_customer=1)
        with frozen_now(NOW), self.assertRaises(BusinessError) as e:
            apply_coupon(Order.objects.create(**{f.name: getattr(v[0], f.name) for f in Order._meta.fields
                                                 if f.name not in ("id",)} | {"status": "pending_payment"}),
                         self.customer, "X")
        self.assertEqual(e.exception.detail["code"], "coupon_not_on_subscription")
        # cancelling early: reschedule instead
        with frozen_now(NOW), self.assertRaises(BusinessError) as e:
            cancel_by_customer(v[1])
        self.assertEqual(e.exception.detail["code"], "subscription_visit_reschedule")
        # reschedule inside the month: fine; outside: no
        with frozen_now(NOW):
            reschedule(v[1], cairo(WED + timedelta(days=1), 12))
            with self.assertRaises(BusinessError) as e:
                reschedule(v[1], cairo(WED + timedelta(days=30), 12))
        self.assertEqual(e.exception.detail["code"], "invalid_slot")  # also outside the booking window
        self.assertEqual(Order.objects.get(pk=v[1].pk).amount_due, v[1].amount_due)  # same price, no fee

    def test_company_cancel_gives_a_makeup_visit(self):
        period = self.pay_card(self.subscribe().periods.get())
        v = self.visits(period)
        with frozen_now(NOW):
            close_day(WED + timedelta(days=7), None, "مطر", self.manager)
        period.refresh_from_db()
        self.assertEqual(period.makeup_visits, 1)
        self.assertFalse(Payment.objects.filter(status="refund_due").exists())  # paid with the month
        with frozen_now(NOW):
            o = service.book_makeup(period, self.customer, cairo(WED + timedelta(days=8), 12))
        self.assertEqual((o.status, o.amount_due, o.amount_to_collect), ("confirmed", 0, 0))
        period.refresh_from_db()
        self.assertEqual(period.makeup_visits, 0)
        with frozen_now(NOW), self.assertRaises(BusinessError):
            service.book_makeup(period, self.customer, cairo(WED + timedelta(days=9), 12))
        self.assertEqual(Order.objects.get(pk=v[1].pk).status, "cancelled_by_company")

    def test_no_rewards_on_visits(self):
        Setting.objects.filter(key="cashback-enabled").update(value=True)
        period = self.pay_card(self.subscribe().periods.get())
        o = self.visits(period)[0]
        end = work_until_done_photos(o, self.tech, START)
        with frozen_now(end):
            o.refresh_from_db()
            complete_job(o, self.tech)
        self.assertFalse(WalletEntry.objects.filter(kind="cashback").exists())
        from loyalty.wash_card import progress

        self.assertEqual(progress(self.customer), 0)
        # and a normal order of the same customer does not get any subscription price
        n = book(self.customer, self.car, self.address, cairo(WED + timedelta(days=2), 15))
        self.assertEqual(n.extra_discount_kind, "")

    def test_renewal(self):
        sub = self.subscribe()
        period = self.pay_card(sub.periods.get())
        with frozen_now(cairo(period.end_date - timedelta(days=4), 9)):
            self.assertEqual(service.renewal_reminders(), 0)
        with frozen_now(cairo(period.end_date - timedelta(days=3), 9)):
            self.assertEqual(service.renewal_reminders(), 1)
            self.assertEqual(service.renewal_reminders(), 0)  # once
        with frozen_now(cairo(period.end_date - timedelta(days=2), 9)):
            p2 = service.renew(sub, self.customer)
        self.assertEqual((p2.number, p2.start_date), (2, period.end_date + timedelta(days=1)))
        self.assertEqual(p2.start_date.weekday(), START.weekday())
        self.assertEqual(p2.visits.count(), 4)

    def test_stop_renewal_ends_after_the_month(self):
        sub = self.subscribe()
        period = self.pay_card(sub.periods.get())
        service.stop_renewal(sub, self.customer)
        with frozen_now(cairo(period.end_date - timedelta(days=3), 9)):
            self.assertEqual(service.renewal_reminders(), 0)
        with frozen_now(cairo(period.end_date + timedelta(days=1), 9)):
            service.end_finished()
        sub.refresh_from_db()
        self.assertEqual(sub.status, "ended")

    def test_api(self):
        api = APIClient()
        api.force_authenticate(self.customer)
        with frozen_now(NOW):
            plans = api.get("/api/subscription-plans/", {"car": self.car.id, "address": self.address.id}).json()
            self.assertEqual((plans[0]["price"], plans[0]["normal_price"], plans[0]["every_days"]), (82600, 97200, 7))
            r = api.post("/api/my-subscriptions/", {"plan": self.plan.id, "car": self.car.id,
                                                    "address": self.address.id, "start": START.isoformat()},
                         format="json")
            self.assertEqual(r.status_code, 201, r.content)
            period_id = r.json()["current"]["id"]
            self.assertEqual(len(r.json()["current"]["visits"]), 4)
            r = api.post(f"/api/subscription-periods/{period_id}/pay-online/", {}, format="json")
            self.assertEqual(r.status_code, 201, r.content)
            page = self.client.post(f"/api/pay/fake/{r.json()['ref']}/", {"action": "pay"})
            self.assertContains(page, "اتدفع")
        mine = api.get("/api/my-subscriptions/").json()
        self.assertEqual(mine[0]["current"]["status"], "paid")
        api.force_authenticate(self.manager)
        rep = api.get("/api/manage/reports/subscriptions/", {"month": NOW.strftime("%Y-%m")}).json()
        self.assertEqual((rep["months_paid"], rep["new"], rep["revenue"], rep["discount_given"]), (1, 1, 82600, 14600))
        self.assertEqual(len(api.get("/api/manage/subscriptions/").json()), 1)
        from services.models import Service

        oil = Service.objects.get(is_oil_change=True)
        r = api.post("/api/manage/subscription-plans/", {"name": "x", "washes_per_month": 2, "services": [oil.id],
                                                         "discount_percent": 10}, format="json")
        self.assertEqual(r.status_code, 400)


@override_settings(MEDIA_ROOT=MEDIA, PAYMENT_GATEWAY="fake")
class CardRefundTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)
        with frozen_now(NOW):
            p = online.start(self.order, self.customer)
            online.handle_callback("fake", paid_callback(p))
            cancel_by_customer(self.order)

    def test_customer_sends_it_back_to_the_card(self):
        api = APIClient()
        api.force_authenticate(self.customer)
        o = api.get(f"/api/orders/{self.order.id}/").json()
        self.assertEqual(o["card_refund_due"], 24300)
        r = api.post(f"/api/orders/{self.order.id}/refund-to-card/")
        self.assertEqual(r.json(), {"refunded": 24300})
        self.assertEqual(Payment.objects.get().status, "refunded")
        self.assertEqual(api.post(f"/api/orders/{self.order.id}/refund-to-card/").json()["code"], "nothing_to_refund")

    def test_back_to_the_card_by_itself_after_a_day(self):
        with frozen_now(NOW + timedelta(hours=23)):
            self.assertEqual(online.auto_refund_cards(), 0)
        with frozen_now(NOW + timedelta(hours=25)):
            self.assertEqual(online.auto_refund_cards(), 1)
        self.assertEqual(Payment.objects.get().status, "refunded")
