"""Invoices: BR-<year>-<6 digits>, restarting each year, no gaps and no
skipped numbers, issued only when the job is completed; a cancelled
invoice keeps its number and is never deleted."""
from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings

from accounts.models import User
from core.errors import BusinessError
from orders.lifecycle import complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments.invoices import cancel_invoice, issue_invoice
from payments.models import Invoice
from payments.payments import confirm_with_payment

from .helpers import MEDIA, book, work_until_done_photos


@override_settings(MEDIA_ROOT=MEDIA)
class InvoiceNumberTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()

    def finish(self, start):
        order = book(self.customer, self.car, self.address, start)
        with frozen_now(start - timedelta(days=1)):
            confirm_with_payment(order, "cash")
        end = work_until_done_photos(order, self.tech, start)
        with frozen_now(end):
            complete_job(order, self.tech, cash_collected=order.amount_due)
        return Invoice.objects.get(order=order)

    def test_no_invoice_before_completion(self):
        order = book(self.customer, self.car, self.address, cairo(WED, 10))
        with frozen_now(cairo(WED, 10) - timedelta(days=1)):
            confirm_with_payment(order, "cash")
        self.assertFalse(Invoice.objects.exists())
        with self.assertRaises(BusinessError):
            issue_invoice(order)

    def test_consecutive_numbers_and_content(self):
        a = self.finish(cairo(WED, 10))
        b = self.finish(cairo(WED, 13))
        self.assertEqual((a.number, b.number), ("BR-2026-000001", "BR-2026-000002"))
        self.assertEqual(a.total, 24300)
        self.assertEqual(a.cash_amount, 24300)
        self.assertEqual(a.lines["cars"][0]["services"][0]["name"], "غسيل خارجي")
        self.assertEqual(a.discount, 2700)

    def test_numbers_restart_each_year(self):
        self.finish(cairo(WED, 10))
        jan = cairo(WED, 10).replace(year=2027, month=1, day=6)  # a Wednesday
        inv = self.finish(jan)
        self.assertEqual(inv.number, "BR-2027-000001")

    def test_failed_completion_leaves_no_gap(self):
        order = book(self.customer, self.car, self.address, cairo(WED, 10))
        with frozen_now(cairo(WED, 10) - timedelta(days=1)):
            confirm_with_payment(order, "cash")
        end = work_until_done_photos(order, self.tech, cairo(WED, 10))
        with frozen_now(end):
            with mock.patch("orders.lifecycle._after_completion", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    complete_job(order, self.tech, cash_collected=order.amount_due)
        self.assertFalse(Invoice.objects.exists())
        self.assertEqual(self.finish(cairo(WED, 13)).number, "BR-2026-000001")

    def test_cancelled_invoice_keeps_number_and_is_never_deleted(self):
        a = self.finish(cairo(WED, 10))
        with self.assertRaises(BusinessError):
            cancel_invoice(a, self.manager, "")
        with frozen_now(cairo(WED, 20)):
            cancel_invoice(a, self.manager, "الفاتورة اتعملت غلط")
        a.refresh_from_db()
        self.assertEqual((a.status, a.cancelled_by, a.cancel_reason), ("cancelled", self.manager, "الفاتورة اتعملت غلط"))
        with self.assertRaises(ValueError):
            a.delete()
        b = self.finish(cairo(WED, 13))
        self.assertEqual(b.number, "BR-2026-000002")  # number 1 is not reused
        with self.assertRaises(BusinessError):
            cancel_invoice(a, self.manager, "تاني")

    def test_one_live_invoice_per_order(self):
        a = self.finish(cairo(WED, 10))
        with self.assertRaises(BusinessError):
            issue_invoice(a.order)
