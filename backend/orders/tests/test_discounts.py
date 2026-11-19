"""One extra discount per order (agreed with John, 19 Nov 2026): the bundle
always applies; on top of it only the biggest of coupon / wash card / referral."""
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.errors import BusinessError
from core.services import get_setting
from coupons.models import Coupon, CouponUse
from coupons.service import apply_coupon, remove_coupon
from orders import discounts
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments.payments import confirm_with_payment
from payments.tests.helpers import MEDIA, book

START = cairo(WED, 10)
NOW = START - timedelta(days=1)


class fake_provider:
    """Pretend a later step (wash card / referral) offers `amount` to every order."""

    def __init__(self, kind, amount):
        self.kind, self.amount = kind, amount

    def __enter__(self):
        self.old = discounts._PROVIDERS.get(self.kind)
        discounts._PROVIDERS[self.kind] = lambda order: self.amount
        return self

    def __exit__(self, *a):
        if self.old is None:
            discounts._PROVIDERS.pop(self.kind, None)
        else:
            discounts._PROVIDERS[self.kind] = self.old


@override_settings(MEDIA_ROOT=MEDIA)
class OneExtraDiscountTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)  # basic bundle: 243 EGP
        Coupon.objects.create(code="TWENTY", kind="amount", value=2000, expires_at=START + timedelta(days=30),
                              max_uses_total=100, max_uses_per_customer=1)

    def apply(self, code="TWENTY"):
        with frozen_now(NOW):
            return apply_coupon(self.order, self.customer, code)

    def test_no_extra_discount(self):
        o = discounts.refresh(self.order)
        self.assertEqual((o.extra_discount_kind, o.extra_discount, o.amount_due), ("", 0, 24300))

    def test_coupon_alone(self):
        o = self.apply()
        self.assertEqual((o.extra_discount_kind, o.extra_discount, o.amount_due), ("coupon", 2000, 22300))

    def test_bigger_other_discount_wins_and_coupon_is_refused(self):
        with fake_provider("wash_card", 12150):  # 50% of 243
            with self.assertRaises(BusinessError) as e:
                self.apply()
            self.assertEqual(e.exception.detail["code"], "better_discount")
            self.assertFalse(CouponUse.objects.exists())  # not counted as used
            o = discounts.refresh(self.order)
            # 121.50 -> whole pounds: discount 121, pays 122
            self.assertEqual((o.extra_discount_kind, o.extra_discount, o.amount_due), ("wash_card", 12100, 12200))

    def test_bigger_coupon_beats_smaller_other(self):
        with fake_provider("referral", 1000):
            o = self.apply()
            self.assertEqual((o.extra_discount_kind, o.extra_discount), ("coupon", 2000))
            # removing the coupon falls back to the other one
            with frozen_now(NOW):
                o = remove_coupon(o, self.customer)
            self.assertEqual((o.extra_discount_kind, o.extra_discount), ("referral", 1000))

    def test_only_one_never_added_together(self):
        with fake_provider("referral", 1500), fake_provider("wash_card", 1000):
            o = self.apply()
            self.assertEqual(o.extra_discount, 2000)  # not 2000 + 1500 + 1000
            self.assertEqual(o.amount_due, 24300 - 2000)

    def test_never_more_than_services(self):
        with fake_provider("wash_card", 10 ** 7):
            o = discounts.refresh(self.order)
            self.assertEqual((o.extra_discount, o.amount_due), (24300, 0))

    def test_confirm_stops_if_discount_changed(self):
        self.apply()
        with fake_provider("wash_card", 10000):  # appeared after the customer saw the price
            pass
        # nothing changed: confirm works
        with frozen_now(NOW):
            o = confirm_with_payment(self.order, "cash")
        self.assertEqual(o.amount_due, 22300)

    def test_confirm_refuses_when_discount_changes_meanwhile(self):
        self.apply()
        CouponUse.objects.all().delete()  # e.g. the coupon was removed somewhere else
        with frozen_now(NOW), self.assertRaises(BusinessError) as e:
            confirm_with_payment(self.order, "cash")
        self.assertEqual(e.exception.detail["code"], "discount_changed")
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.amount_due), ("pending_payment", 24300))  # new price saved

    def test_api_shows_kind_and_label(self):
        self.apply()
        api = APIClient()
        api.force_authenticate(self.customer)
        r = api.get(f"/api/orders/{self.order.id}/").json()
        self.assertEqual((r["extra_discount_kind"], r["extra_discount_label"], r["extra_discount"], r["coupon_code"]),
                         ("coupon", "كوبون", 2000, "TWENTY"))


class LoyaltySettingsTests(TestCase):
    def test_starting_values_agreed_with_john(self):
        expected = {
            "cashback-enabled": False, "cashback-percent": 5,
            "wash-card-enabled": True, "wash-card-every-n": 5, "wash-card-reward-percent": 50,
            "referral-enabled": True, "referral-new-customer-discount": 5000, "referral-referrer-credit": 5000,
            "referral-monthly-cap": 5, "refund-to-wallet-bonus-percent": 10, "winback-after-days": 30,
        }
        self.assertEqual({k: get_setting(k) for k in expected}, expected)
