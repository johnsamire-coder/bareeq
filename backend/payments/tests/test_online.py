"""Paying online (card / mobile wallet), phase 3 step 1. The order is confirmed
only by the payment company's signed message; never twice; wrong amounts and
fake messages are refused; money that comes after the booking was lost is
marked to be returned."""
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from core.errors import BusinessError
from core.models import Setting
from notifications.models import Notification
from orders.booking import expire_holds
from orders.lifecycle import cancel_by_customer, complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments import online, wallet
from payments.gateway.fake import sign
from payments.models import OnlinePayment, Payment

from .helpers import MEDIA, book, work_until_done_photos

START = cairo(WED, 10)
NOW = START - timedelta(days=1)


def callback_data(p, paid=True, amount=None, txn="T-1"):
    amount = p.amount if amount is None else amount
    return {"ref": p.ref, "paid": "1" if paid else "0", "amount": amount, "txn_id": txn,
            "signature": sign(p.ref, paid, amount, txn)}


@override_settings(MEDIA_ROOT=MEDIA, PAYMENT_GATEWAY="fake")
class OnlinePaymentTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)  # 243 EGP

    def start(self, wallet_amount=0):
        with frozen_now(NOW):
            return online.start(self.order, self.customer, wallet_amount)

    def pay(self, p, **kw):
        with frozen_now(NOW + timedelta(minutes=2)):
            return online.handle_callback("fake", callback_data(p, **kw))

    def test_paid_confirms_the_order_once(self):
        p = self.start()
        self.order.refresh_from_db()
        self.assertEqual((p.amount, self.order.status), (24300, "pending_payment"))  # not before the company says so
        self.pay(p)
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.payment_method, self.order.amount_to_collect),
                         ("confirmed", "card", 0))
        pay = Payment.objects.get()
        self.assertEqual((pay.method, pay.amount, pay.status), ("card", 24300, "confirmed"))
        self.pay(p)  # the same message again
        self.assertEqual(Payment.objects.count(), 1)
        self.assertTrue(Notification.objects.filter(user=self.customer, kind="booking_confirmed").exists())

    def test_wallet_part_taken_only_when_paid(self):
        wallet.credit(self.customer, 10000, "manual", created_by=self.manager, note="هدية")
        p = self.start(wallet_amount=5000)
        self.assertEqual(p.amount, 19300)
        self.assertEqual(wallet.balance(self.customer), 10000)  # nothing taken yet
        self.pay(p)
        self.order.refresh_from_db()
        self.assertEqual((wallet.balance(self.customer), self.order.wallet_used), (5000, 5000))

    def test_failed_payment_leaves_order_waiting(self):
        p = self.start()
        p = self.pay(p, paid=False)
        self.order.refresh_from_db()
        self.assertEqual((p.status, self.order.status), ("failed", "pending_payment"))
        self.assertFalse(Payment.objects.exists())
        p2 = self.start()  # can try again
        self.pay(p2)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "confirmed")

    def test_fake_message_refused(self):
        p = self.start()
        data = callback_data(p)
        data["signature"] = "0" * 64
        with self.assertRaises(BusinessError) as e:
            online.handle_callback("fake", data)
        self.assertEqual(e.exception.detail["code"], "bad_signature")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending_payment")

    def test_wrong_amount_refused_and_manager_told(self):
        p = self.start()
        p = self.pay(p, amount=100)
        self.order.refresh_from_db()
        self.assertEqual((p.status, self.order.status), ("failed", "pending_payment"))
        self.assertTrue(Notification.objects.filter(user=self.manager, kind="online_payment_problem").exists())

    def test_hold_kept_longer_while_paying(self):
        before = self.order.hold_expires_at
        self.start()
        self.order.refresh_from_db()
        self.assertEqual(self.order.hold_expires_at, before + timedelta(minutes=15))  # 15 more minutes
        self.assertGreater(self.order.hold_expires_at, before)

    def test_money_after_booking_lost_is_to_be_returned(self):
        p = self.start()
        with frozen_now(NOW + timedelta(hours=1)):
            expire_holds()
        self.pay(p)
        p.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual((p.status, self.order.status), ("late", "expired"))
        self.assertEqual(Payment.objects.get().status, "refund_due")
        self.assertTrue(Notification.objects.filter(user=self.manager, title="فلوس لازم ترجع").exists())

    def test_switched_off(self):
        Setting.objects.filter(key="card-payment-enabled").update(value=False)
        with self.assertRaises(BusinessError) as e:
            self.start()
        self.assertEqual(e.exception.detail["code"], "payment_method_not_available")

    def test_cancelled_card_order_money_to_return_or_wallet(self):
        self.pay(self.start())
        with frozen_now(NOW):
            cancel_by_customer(self.order)
        self.assertEqual(Payment.objects.get().status, "refund_due")
        from loyalty.refunds import wallet_option

        self.assertEqual(wallet_option(self.order), {"amount": 24300, "bonus": 2400, "wallet_amount": 26700})

    def test_invoice_shows_card(self):
        self.pay(self.start())
        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            self.order.refresh_from_db()
            complete_job(self.order, self.tech)  # nothing to collect
        inv = self.order.invoices.get()
        self.assertEqual((inv.card_amount, inv.cash_amount, inv.total), (24300, 0, 24300))

    def test_api_and_test_page(self):
        api = APIClient()
        api.force_authenticate(self.customer)
        with frozen_now(NOW):
            r = api.post(f"/api/orders/{self.order.id}/pay-online/", {}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        ref, url = r.json()["ref"], r.json()["redirect_url"]
        self.assertTrue(url.endswith(f"/api/pay/fake/{ref}/"))
        page = self.client.get(f"/api/pay/fake/{ref}/")
        self.assertContains(page, "صفحة دفع تجريبية")
        with frozen_now(NOW + timedelta(minutes=1)):
            page = self.client.post(f"/api/pay/fake/{ref}/", {"action": "pay"})
        self.assertContains(page, "اتدفع")
        self.assertEqual(api.get(f"/api/pay/{ref}/").json()["status"], "paid")
        # the company's callback endpoint: same message again is fine; bad one refused
        p = OnlinePayment.objects.get(ref=ref)
        self.assertEqual(self.client.post("/api/pay/callback/fake/", callback_data(p), content_type="application/json"
                                          ).json()["status"], "paid")
        bad = {**callback_data(p), "signature": "x"}
        self.assertEqual(self.client.post("/api/pay/callback/fake/", bad, content_type="application/json").status_code, 403)
        # someone else cannot see it
        other, _, _ = make_customer("01012300000")
        api.force_authenticate(other)
        self.assertEqual(api.get(f"/api/pay/{ref}/").status_code, 404)

    @override_settings(PAYMENT_GATEWAY="paymob")
    def test_test_page_off_on_the_real_server(self):
        self.assertEqual(self.client.get("/api/pay/fake/abc/").status_code, 404)
