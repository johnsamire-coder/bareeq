"""Wallet ledger (SPEC 11). Gift balance only; every change is a row.

- Each credit has an expiry date (90 days, setting) and a 'remaining' part.
- Spending uses the credits that expire first.
- When a credit expires, an 'expiry' row removes what is left of it.
- Balance = what is left of credits that have not expired yet. After the
  expiry job runs, it also equals the plain sum of all rows.
- At most 50% (setting) of an order can be paid from the wallet.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Sum
from django.test import TestCase

from accounts.models import User
from core.errors import BusinessError
from core.models import Setting
from payments import wallet
from payments.models import WalletEntry

from orders.tests.helpers import frozen_now

T0 = datetime(2026, 11, 18, 12, tzinfo=ZoneInfo("Africa/Cairo"))


class WalletTests(TestCase):
    def setUp(self):
        self.c = User.objects.create_user("01012345678", "عميل")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")

    def ledger_sum(self):
        return WalletEntry.objects.filter(customer=self.c).aggregate(s=Sum("amount"))["s"] or 0

    def test_credit_default_expiry_90_days(self):
        with frozen_now(T0):
            e = wallet.credit(self.c, 10000, "manual", created_by=self.manager, note="هدية")
            self.assertEqual(wallet.balance(self.c), 10000)
        self.assertEqual(e.expires_at, T0 + timedelta(days=90))
        self.assertEqual(e.remaining, 10000)

    def test_spend_uses_soonest_expiring_first(self):
        with frozen_now(T0):
            a = wallet.credit(self.c, 5000, "manual", expires_at=T0 + timedelta(days=10), created_by=self.manager, note="a")
            b = wallet.credit(self.c, 10000, "manual", expires_at=T0 + timedelta(days=90), created_by=self.manager, note="b")
            wallet.spend(self.c, 7000)
            a.refresh_from_db(); b.refresh_from_db()
            self.assertEqual((a.remaining, b.remaining), (0, 8000))
            self.assertEqual(wallet.balance(self.c), 8000)
        with frozen_now(T0 + timedelta(days=11)):
            self.assertEqual(wallet.expire_credits(), 0)  # nothing left in 'a' to expire
            self.assertEqual(wallet.balance(self.c), 8000)
        self.assertEqual(self.ledger_sum(), 8000)

    def test_expiry_removes_only_what_is_left(self):
        with frozen_now(T0):
            wallet.credit(self.c, 10000, "manual", created_by=self.manager, note="x")
            wallet.spend(self.c, 3000)
        later = T0 + timedelta(days=90, minutes=1)
        with frozen_now(later):
            self.assertEqual(wallet.balance(self.c), 0)  # expired even before the job runs
            self.assertEqual(wallet.expire_credits(), 1)
            self.assertEqual(wallet.expire_credits(), 0)  # runs twice safely
        expiry = WalletEntry.objects.get(kind="expiry")
        self.assertEqual(expiry.amount, -7000)
        self.assertEqual(self.ledger_sum(), 0)

    def test_cannot_spend_more_than_balance_or_expired(self):
        with frozen_now(T0):
            wallet.credit(self.c, 5000, "manual", expires_at=T0 + timedelta(days=1), created_by=self.manager, note="x")
            with self.assertRaises(BusinessError):
                wallet.spend(self.c, 5001)
        with frozen_now(T0 + timedelta(days=2)):
            with self.assertRaises(BusinessError):
                wallet.spend(self.c, 1)
        with self.assertRaises(BusinessError):
            wallet.spend(self.c, 0)

    def test_manual_credit_needs_manager_and_note(self):
        with self.assertRaises(BusinessError):
            wallet.credit(self.c, 1000, "manual", created_by=self.manager, note="  ")
        with self.assertRaises(BusinessError):
            wallet.credit(self.c, 1000, "manual", created_by=None, note="x")
        with self.assertRaises(BusinessError):
            wallet.credit(self.c, -5, "manual", created_by=self.manager, note="x")

    def test_expiry_days_is_a_setting(self):
        Setting.objects.filter(key="wallet-credit-expiry-days").update(value=30)
        with frozen_now(T0):
            e = wallet.credit(self.c, 1000, "manual", created_by=self.manager, note="x")
        self.assertEqual(e.expires_at, T0 + timedelta(days=30))

    def test_max_share_of_order(self):
        self.assertEqual(wallet.max_usable_for(24300), 12150)
        self.assertEqual(wallet.max_usable_for(24301), 12150)  # never rounds up past 50%
        Setting.objects.filter(key="wallet-max-order-share-percent").update(value=20)
        self.assertEqual(wallet.max_usable_for(24300), 4860)

    def test_rows_are_never_edited_or_deleted(self):
        with frozen_now(T0):
            e = wallet.credit(self.c, 1000, "manual", created_by=self.manager, note="x")
        with self.assertRaises(ValueError):
            e.delete()
        e.amount = 99999
        with self.assertRaises(ValueError):
            e.save()
