"""seed_demo_accounts: the three accounts to try the app on the test server."""
import io
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import User
from orders.models import Order
from orders.tests.helpers import WED, cairo, frozen_now
from payments.tests.helpers import MEDIA


@override_settings(MEDIA_ROOT=MEDIA)
class DemoAccountsTests(TestCase):
    def test_three_accounts_and_an_order_for_the_demo_technician(self):
        with frozen_now(cairo(WED, 8)):
            out = io.StringIO()
            call_command("seed_demo_accounts", stdout=out)
            call_command("seed_demo_accounts", stdout=io.StringIO())  # again: nothing twice
        self.assertEqual(User.objects.get(phone="+201000000001").role, "manager")
        customer = User.objects.get(phone="+201000000002")
        self.assertFalse(customer.needs_terms_acceptance)
        tech = User.objects.get(phone="+201000000101")
        orders = Order.objects.filter(customer=customer, status="confirmed")
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.get().technician, tech)
        self.assertGreater(orders.get().scheduled_start, cairo(WED, 8) + timedelta(hours=12))
        self.assertIn("01000000001", out.getvalue())
