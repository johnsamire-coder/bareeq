"""Paying: cash to the technician, InstaPay with a screenshot confirmed by the
manager, and up to 50% from the wallet."""
from datetime import timedelta

from django.test import TestCase, override_settings

from accounts.models import User
from core.errors import BusinessError
from orders.lifecycle import cancel_by_customer, complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments import wallet
from payments.models import Invoice, Payment, WalletEntry
from payments.payments import confirm_with_payment, review_instapay

from .helpers import MEDIA, book, proof, work_until_done_photos

START = cairo(WED, 10)
BEFORE = START - timedelta(days=1)


@override_settings(MEDIA_ROOT=MEDIA)
class PaymentFlowTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)  # 243 EGP

    def confirm(self, method, **kw):
        with frozen_now(BEFORE):
            return confirm_with_payment(self.order, method, **kw)

    def complete(self, **kw):
        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            return complete_job(self.order, self.tech, **kw)

    def test_cash(self):
        o = self.confirm("cash")
        self.assertEqual((o.status, o.payment_method, o.amount_to_collect), ("confirmed", "cash", 24300))
        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            with self.assertRaises(BusinessError) as e:
                complete_job(self.order, self.tech)
            self.assertEqual(e.exception.detail["code"], "cash_amount_required")
            complete_job(self.order, self.tech, cash_collected=24000)  # 3 EGP short
        p = Payment.objects.get(method="cash")
        self.assertEqual((p.amount, p.status, p.collected_by), (24000, "collected", self.tech))
        inv = Invoice.objects.get()
        self.assertEqual((inv.cash_amount, inv.total), (24000, 24300))

    def test_wallet_part(self):
        with frozen_now(BEFORE - timedelta(days=1)):
            wallet.credit(self.customer, 20000, "manual", created_by=self.manager, note="تعويض")
        with self.assertRaises(BusinessError) as e:
            self.confirm("cash", wallet_amount=12200)  # more than 50% of 243 (= 121 whole pounds)
        self.assertEqual(e.exception.detail["code"], "wallet_over_limit")
        o = self.confirm("cash", wallet_amount=12150)  # 121.50 -> rounded down to 121
        self.assertEqual((o.wallet_used, o.amount_to_collect), (12100, 12200))
        self.assertEqual(o.amount_to_collect % 100, 0)  # technician collects whole pounds
        with frozen_now(BEFORE):
            self.assertEqual(wallet.balance(self.customer), 7900)
        self.complete(cash_collected=12200)
        inv = Invoice.objects.get()
        self.assertEqual((inv.wallet_amount, inv.cash_amount), (12100, 12200))
        self.order.refresh_from_db()
        self.assertEqual((self.order.revenue, self.order.collected, self.order.uncollected), (24300, 12200, 0))

    def test_wallet_more_than_balance(self):
        with self.assertRaises(BusinessError) as e:
            self.confirm("cash", wallet_amount=100)
        self.assertEqual(e.exception.detail["code"], "insufficient_wallet")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending_payment")

    def test_instapay_needs_screenshot_then_manager_confirms(self):
        with self.assertRaises(BusinessError) as e:
            self.confirm("instapay")
        self.assertEqual(e.exception.detail["code"], "proof_required")
        o = self.confirm("instapay", proof_file=proof())
        self.assertEqual(o.status, "confirmed")
        p = Payment.objects.get()
        self.assertEqual((p.method, p.amount, p.status), ("instapay", 24300, "pending_review"))
        review_instapay(p, self.manager, approve=True)
        p.refresh_from_db()
        self.assertEqual((p.status, p.reviewed_by), ("confirmed", self.manager))
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_to_collect, 0)
        self.complete()  # nothing to collect in cash
        self.assertEqual(Invoice.objects.get().instapay_amount, 24300)
        self.order.refresh_from_db()
        self.assertEqual((self.order.revenue, self.order.collected, self.order.uncollected), (24300, 24300, 0))

    def test_instapay_rejected_becomes_cash(self):
        self.confirm("instapay", proof_file=proof())
        p = Payment.objects.get()
        with self.assertRaises(BusinessError):
            review_instapay(p, self.manager, approve=False, reason="")
        review_instapay(p, self.manager, approve=False, reason="التحويل مش موجود")
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_to_collect, 24300)
        with self.assertRaises(BusinessError):
            self.complete()
        self.assertEqual(Payment.objects.get(pk=p.pk).status, "rejected")

    def test_cancel_returns_wallet_and_marks_instapay_for_refund(self):
        with frozen_now(BEFORE - timedelta(days=1)):
            wallet.credit(self.customer, 20000, "manual", created_by=self.manager, note="x")
        self.confirm("instapay", proof_file=proof(), wallet_amount=10000)
        with frozen_now(BEFORE):
            cancel_by_customer(self.order)
            self.assertEqual(wallet.balance(self.customer), 20000)
        self.assertTrue(WalletEntry.objects.filter(kind="refund", amount=10000, order=self.order).exists())
        self.assertEqual(Payment.objects.get(method="instapay").status, "refund_due")

    def test_unknown_method(self):
        with self.assertRaises(BusinessError):
            self.confirm("visa")


@override_settings(MEDIA_ROOT=MEDIA)
class WholePoundsRuleTests(TestCase):
    """Everything the customer pays is whole pounds, even with a fee that has piastres."""

    def test_fee_with_piastres_wallet_and_cash(self):
        from core.models import Setting
        from orders.lifecycle import cancel_by_customer

        tech = make_technician("01100000001")
        manager = User.objects.create_user("01000000001", "Boss", role="manager")
        customer, car, address = make_customer()
        Setting.objects.filter(key="cancellation-late-fee").update(value=5025)  # 50.25 EGP
        first = book(customer, car, address, START)
        with frozen_now(BEFORE):
            confirm_with_payment(first, "cash")
        with frozen_now(START - timedelta(hours=1)):
            cancel_by_customer(first)  # late: 50.25 fee
        with frozen_now(BEFORE - timedelta(days=1)):
            wallet.credit(customer, 9999, "manual", created_by=manager, note="x")
        second = book(customer, car, address, cairo(WED, 16))  # 243 + 50.25 fee
        with frozen_now(cairo(WED, 16) - timedelta(days=1)):
            o = confirm_with_payment(second, "cash", wallet_amount=9999)
        self.assertEqual((o.total, o.charges_total, o.rounding, o.amount_due), (24300, 5025, 25, 29300))
        self.assertEqual(o.wallet_used, 9900)
        for amount in (o.amount_due, o.wallet_used, o.amount_to_collect):
            self.assertEqual(amount % 100, 0, amount)
        end = work_until_done_photos(o, tech, cairo(WED, 16))
        with frozen_now(end):
            complete_job(o, tech, cash_collected=o.amount_to_collect)
        inv = Invoice.objects.get()
        self.assertEqual((inv.total, inv.discount, inv.charges_total), (29300, 2700 + 25, 5025))
        self.assertEqual(inv.total % 100, 0)
