"""Simple coupons (client decision 17 Nov 2026, for the launch ad):
code, percent OR fixed amount, expiry date, max uses for everyone and per
customer, optional zone. The discount is on the services (not oil) and the
customer always pays whole pounds. Cancelled / expired orders do not use up a coupon."""
from datetime import timedelta

from django.test import TestCase, override_settings

from accounts.models import User
from core.errors import BusinessError
from coupons.models import Coupon
from coupons.service import apply_coupon, remove_coupon
from orders.lifecycle import cancel_by_customer, complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments import wallet
from payments.models import Invoice
from payments.payments import confirm_with_payment
from payments.tests.helpers import MEDIA, book, work_until_done_photos
from places.models import Zone

START = cairo(WED, 10)
NOW = START - timedelta(days=1)


def coupon(**kw):
    d = dict(code="LAUNCH20", kind="percent", value=20, expires_at=START + timedelta(days=30),
             max_uses_total=100, max_uses_per_customer=1)
    d.update(kw)
    return Coupon.objects.create(**d)


@override_settings(MEDIA_ROOT=MEDIA)
class CouponTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)  # basic bundle: 243 EGP

    def apply(self, code, order=None, now=NOW):
        with frozen_now(now):
            return apply_coupon(order or self.order, self.customer, code)

    def code_of(self, fn):
        with self.assertRaises(BusinessError) as e:
            fn()
        return e.exception.detail["code"]

    def test_percent_whole_pounds(self):
        coupon()
        o = self.apply(" launch20 ")  # any case, spaces ignored
        # 20% of 243 = 48.60 -> discount rounded DOWN to 48 -> pays 195
        self.assertEqual((o.coupon_discount, o.amount_due), (4800, 19500))
        self.assertEqual(o.amount_due % 100, 0)

    def test_fixed_amount_and_never_more_than_services(self):
        coupon(code="FIFTY", kind="amount", value=5000)
        self.assertEqual(self.apply("FIFTY").amount_due, 19300)
        coupon(code="HUGE", kind="amount", value=100000)
        self.assertEqual(self.apply("HUGE").amount_due, 0)  # replaces FIFTY, capped at the services total

    def test_invalid_expired_inactive_zone(self):
        coupon(code="OLD", expires_at=NOW - timedelta(minutes=1))
        coupon(code="OFF", is_active=False)
        coupon(code="OBOUR", zone=Zone.objects.get(name="العبور"))
        coupon(code="NASR", zone=Zone.objects.get(name="مدينة نصر"))
        self.assertEqual(self.code_of(lambda: self.apply("NOPE")), "coupon_invalid")
        self.assertEqual(self.code_of(lambda: self.apply("OLD")), "coupon_expired")
        self.assertEqual(self.code_of(lambda: self.apply("OFF")), "coupon_invalid")
        self.assertEqual(self.code_of(lambda: self.apply("OBOUR")), "coupon_wrong_zone")
        self.assertEqual(self.apply("NASR").coupon_discount, 4800)

    def test_per_customer_limit_and_cancelled_orders_do_not_count(self):
        coupon(max_uses_per_customer=1)
        self.apply("LAUNCH20")
        with frozen_now(NOW):
            confirm_with_payment(self.order, "cash")
        second = book(self.customer, self.car, self.address, cairo(WED, 14))
        self.assertEqual(self.code_of(lambda: self.apply("LAUNCH20", order=second)), "coupon_already_used")
        with frozen_now(NOW):
            cancel_by_customer(self.order)  # free (more than 2 hours before)
        self.assertEqual(self.apply("LAUNCH20", order=second).coupon_discount, 4800)

    def test_total_limit_for_everyone(self):
        coupon(max_uses_total=1)
        self.apply("LAUNCH20")
        with frozen_now(NOW):
            confirm_with_payment(self.order, "cash")
        other, ocar, oaddr = make_customer("01012345670")
        o2 = book(other, ocar, oaddr, cairo(WED, 14))
        with frozen_now(NOW):
            with self.assertRaises(BusinessError) as e:
                apply_coupon(o2, other, "LAUNCH20")
        self.assertEqual(e.exception.detail["code"], "coupon_used_up")

    def test_hold_expiry_frees_the_use(self):
        coupon(max_uses_total=1)
        self.apply("LAUNCH20")  # order held, never paid
        other, ocar, oaddr = make_customer("01012345670")
        o2 = book(other, ocar, oaddr, cairo(WED, 14))
        with frozen_now(NOW + timedelta(minutes=11)):  # hold of the first order expired
            self.assertEqual(apply_coupon(o2, other, "LAUNCH20").coupon_discount, 4800)

    def test_confirm_rechecks_the_limit(self):
        coupon(max_uses_total=1)
        other, ocar, oaddr = make_customer("01012345670")
        o2 = book(other, ocar, oaddr, cairo(WED, 14))
        self.apply("LAUNCH20")
        with frozen_now(NOW):
            apply_coupon(o2, other, "LAUNCH20")  # both held at the same time: allowed for now
            confirm_with_payment(self.order, "cash")
            with self.assertRaises(BusinessError) as e:
                confirm_with_payment(o2, "cash")
        self.assertEqual(e.exception.detail["code"], "coupon_used_up")

    def test_remove_coupon(self):
        coupon()
        self.apply("LAUNCH20")
        with frozen_now(NOW):
            o = remove_coupon(self.order, self.customer)
        self.assertEqual((o.coupon_discount, o.amount_due), (0, 24300))

    def test_only_pending_orders_and_own_order(self):
        coupon()
        with frozen_now(NOW):
            confirm_with_payment(self.order, "cash")
        self.assertEqual(self.code_of(lambda: self.apply("LAUNCH20")), "not_pending")
        other, _, _ = make_customer("01012345670")
        o2 = book(self.customer, self.car, self.address, cairo(WED, 14))
        with frozen_now(NOW):
            with self.assertRaises(BusinessError):
                apply_coupon(o2, other, "LAUNCH20")

    def test_with_wallet_and_invoice(self):
        coupon()
        with frozen_now(NOW - timedelta(days=1)):
            wallet.credit(self.customer, 20000, "manual", created_by=self.manager, note="x")
        self.apply("LAUNCH20")  # pays 195
        with frozen_now(NOW):
            o = confirm_with_payment(self.order, "cash", wallet_amount=9750)  # 97.50 -> rounded down to 97
        self.assertEqual((o.wallet_used, o.amount_to_collect), (9700, 9800))  # 50% of 195 = 97.50 -> 97
        end = work_until_done_photos(o, self.tech, START)
        with frozen_now(end):
            complete_job(o, self.tech, cash_collected=o.amount_to_collect)
        inv = Invoice.objects.get()
        self.assertEqual((inv.total, inv.discount), (19500, 2700 + 4800))
        self.assertEqual(inv.lines["coupon"], {"code": "LAUNCH20", "discount": 4800})
