"""Late-cancellation and car-not-found fees (50 EGP each, settings).

A fee is recorded on the customer, shown before he confirms his next booking,
and added to that next order as its own line. The manager can waive it with a
written reason; who and when are recorded.
"""
from datetime import timedelta

from django.test import TestCase

from accounts.models import User
from core.errors import BusinessError
from core.models import Setting
from orders.booking import available_slots, create_order, expire_holds
from orders.charges import outstanding_charges, waive_charge
from orders.lifecycle import cancel_by_customer, reschedule
from orders.models import CustomerCharge, Order

from .helpers import WED, book_confirmed, cairo, frozen_now, make_customer, make_technician, sid

THU = WED + timedelta(days=1)


class CancellationFeeTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.order = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))

    def test_free_until_two_hours_before(self):
        with frozen_now(cairo(WED, 12)):  # exactly 2 hours before
            cancel_by_customer(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled_by_customer")
        self.assertFalse(CustomerCharge.objects.exists())

    def test_late_cancel_costs_50(self):
        with frozen_now(cairo(WED, 12, 1)):
            cancel_by_customer(self.order)
        charge = CustomerCharge.objects.get()
        self.assertEqual((charge.kind, charge.amount, charge.source_order), ("late_cancellation", 5000, self.order))
        self.assertEqual(outstanding_charges(self.customer), [charge])

    def test_fee_and_window_are_settings(self):
        Setting.objects.filter(key="cancellation-late-fee").update(value=7500)
        Setting.objects.filter(key="cancellation-free-until-hours").update(value=3)
        with frozen_now(cairo(WED, 11, 30)):
            cancel_by_customer(self.order)
        self.assertEqual(CustomerCharge.objects.get().amount, 7500)

    def test_unconfirmed_hold_cancel_is_free(self):
        with frozen_now(cairo(WED, 13)):
            o = create_order(self.customer, self.address.id,
                             [{"car": self.car.id, "services": sid("exterior-wash")}], cairo(WED, 17))
            cancel_by_customer(o)
        self.assertFalse(CustomerCharge.objects.exists())

    def test_cannot_cancel_after_technician_left(self):
        Order.objects.filter(pk=self.order.pk).update(status="on_the_way")
        self.order.refresh_from_db()
        with frozen_now(cairo(WED, 10)):
            with self.assertRaises(BusinessError):
                cancel_by_customer(self.order)

    def test_late_reschedule_costs_50_free_reschedule_costs_nothing(self):
        with frozen_now(cairo(WED, 9)):
            reschedule(self.order, cairo(WED, 18))
        self.assertFalse(CustomerCharge.objects.exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.scheduled_start, cairo(WED, 18))
        with frozen_now(cairo(WED, 17)):
            reschedule(self.order, cairo(THU, 10))
        self.assertEqual(CustomerCharge.objects.get().kind, "late_reschedule")


class ChargeOnNextOrderTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        first = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))
        with frozen_now(cairo(WED, 13)):
            cancel_by_customer(first)
        self.items = [{"car": self.car.id, "services": sid("exterior-wash")}]

    def test_shown_before_booking_and_added_as_own_line(self):
        with frozen_now(cairo(WED, 13)):
            slots = available_slots(self.customer, self.address.id, self.items)
            self.assertEqual(slots["charges_total"], 5000)
            self.assertEqual(slots["charges"][0]["kind"], "late_cancellation")
            self.assertEqual(slots["total"], 15000)
            self.assertEqual(slots["amount_due"], 20000)
            o = create_order(self.customer, self.address.id, self.items, cairo(THU, 10))
        self.assertEqual((o.total, o.charges_total, o.amount_due), (15000, 5000, 20000))
        self.assertEqual(outstanding_charges(self.customer), [])
        self.assertEqual(CustomerCharge.objects.get().applied_to_order, o)

    def test_charge_comes_back_if_next_order_does_not_happen(self):
        with frozen_now(cairo(WED, 13)):
            o = create_order(self.customer, self.address.id, self.items, cairo(THU, 10))
        with frozen_now(cairo(WED, 13, 11)):
            expire_holds()
        self.assertEqual(len(outstanding_charges(self.customer)), 1)
        with frozen_now(cairo(WED, 13, 12)):
            o2 = create_order(self.customer, self.address.id, self.items, cairo(THU, 10))
            cancel_by_customer(o2)  # unconfirmed: free, and the old fee is released again
        self.assertEqual(len(outstanding_charges(self.customer)), 1)


class WaiveTests(TestCase):
    def setUp(self):
        make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        first = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))
        with frozen_now(cairo(WED, 13)):
            cancel_by_customer(first)
        self.charge = CustomerCharge.objects.get()

    def test_waive_needs_reason_and_records_who_and_when(self):
        with self.assertRaises(BusinessError):
            waive_charge(self.charge, self.manager, "   ")
        with frozen_now(cairo(WED, 15)):
            waive_charge(self.charge, self.manager, "العميل كان عنده ظرف طارئ")
        self.charge.refresh_from_db()
        self.assertEqual(self.charge.waived_by, self.manager)
        self.assertEqual(self.charge.waived_at, cairo(WED, 15))
        self.assertEqual(self.charge.waive_reason, "العميل كان عنده ظرف طارئ")
        self.assertEqual(outstanding_charges(self.customer), [])

    def test_waive_removes_it_from_open_order(self):
        with frozen_now(cairo(WED, 13)):
            o = create_order(self.customer, self.address.id, [{"car": self.car.id, "services": sid("exterior-wash")}],
                             cairo(THU, 10))
        waive_charge(self.charge, self.manager, "سماح")
        o.refresh_from_db()
        self.assertEqual((o.charges_total, o.amount_due), (0, 15000))

    def test_cannot_waive_twice_or_after_paid(self):
        waive_charge(self.charge, self.manager, "سماح")
        with self.assertRaises(BusinessError):
            waive_charge(self.charge, self.manager, "تاني")
