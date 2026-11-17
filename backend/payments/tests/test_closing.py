"""Materials per job (manager's list, unit and unit price; technician types the
quantity) and the technician's daily cash closing confirmed by the manager."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings

from accounts.models import User
from core.errors import BusinessError
from orders.lifecycle import complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments.closing import closing_summary, confirm_closing, record_materials, submit_closing
from payments.models import DailyClosing, Material
from payments.payments import confirm_with_payment

from .helpers import MEDIA, book, work_until_done_photos


@override_settings(MEDIA_ROOT=MEDIA)
class MaterialsAndClosingTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.shampoo = Material.objects.create(name="شامبو تجربة", unit="liter", unit_cost=8000)  # 80 EGP / liter
        self.cloth = Material.objects.create(name="فوطة تجربة", unit="piece", unit_cost=1500)

    def done_job(self, start, cash):
        order = book(self.customer, self.car, self.address, start)
        with frozen_now(start - timedelta(days=1)):
            confirm_with_payment(order, "cash")
        end = work_until_done_photos(order, self.tech, start)
        with frozen_now(end):
            complete_job(order, self.tech, cash_collected=cash)
        return order

    def test_material_cost_and_wash_margin(self):
        order = self.done_job(cairo(WED, 10), 24300)
        record_materials(order, self.tech, [{"material": self.shampoo.id, "quantity": "0.5"},
                                            {"material": self.cloth.id, "quantity": "2"}])
        order.refresh_from_db()
        self.assertEqual(order.materials_cost, 4000 + 3000)
        self.assertEqual(order.wash_margin, 24300 - 7000)
        # Price change later does not change past jobs.
        self.shampoo.unit_cost = 10000
        self.shampoo.save()
        record_materials(order, self.tech, [{"material": self.cloth.id, "quantity": "1"}])  # replaces the list
        order.refresh_from_db()
        self.assertEqual(order.materials_cost, 1500)

    def test_material_quantity_checks(self):
        order = self.done_job(cairo(WED, 10), 24300)
        for bad in ("0", "-1", "abc"):
            with self.assertRaises(BusinessError):
                record_materials(order, self.tech, [{"material": self.shampoo.id, "quantity": bad}])
        other = make_technician("01100000002")
        with self.assertRaises(BusinessError):
            record_materials(order, other, [{"material": self.shampoo.id, "quantity": "1"}])

    def test_daily_closing(self):
        self.done_job(cairo(WED, 10), 24300)
        self.done_job(cairo(WED, 13), 24000)  # customer paid 3 EGP less
        s = closing_summary(self.tech, WED)
        self.assertEqual(s["cash_collected"], 48300)
        # Revenue next to collected: 300 piastres missing (no wallet used here).
        self.assertEqual((s["revenue"], s["collected"], s["wallet_used"], s["uncollected"]), (48600, 48300, 0, 300))
        self.assertEqual(len(s["orders"]), 2)
        with frozen_now(cairo(WED, 22)):
            c = submit_closing(self.tech, WED, cash_handed=48000, note="")
        self.assertEqual((c.cash_expected, c.cash_handed, c.difference), (48300, 48000, -300))
        # Can resubmit until confirmed.
        with frozen_now(cairo(WED, 22, 5)):
            c = submit_closing(self.tech, WED, cash_handed=48300, note="لقيت الـ 3 جنيه")
        self.assertEqual(c.difference, 0)
        self.assertEqual(DailyClosing.objects.count(), 1)
        with frozen_now(cairo(WED, 23)):
            confirm_closing(c, self.manager)
        c.refresh_from_db()
        self.assertEqual((c.status, c.confirmed_by), ("confirmed", self.manager))
        with self.assertRaises(BusinessError):
            submit_closing(self.tech, WED, cash_handed=1, note="")
        # Materials of a closed day cannot change.
        order = c.technician.jobs.first()
        with self.assertRaises(BusinessError):
            record_materials(order, self.tech, [{"material": self.shampoo.id, "quantity": "1"}])
