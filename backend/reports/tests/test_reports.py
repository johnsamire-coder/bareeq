"""Reports: revenue next to collected and wallet, margin, breakdowns, new vs
returning customers, real job time vs planned. Customers list and file."""
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from orders.lifecycle import cancel_by_customer, complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments import wallet
from payments.closing import record_materials
from payments.models import Material
from payments.payments import confirm_with_payment
from payments.tests.helpers import MEDIA, book, work_until_done_photos


@override_settings(MEDIA_ROOT=MEDIA)
class ReportTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.c = APIClient()
        self.c.force_authenticate(self.manager)

    def finish(self, customer, car, address, start, services=("exterior-wash",), wallet_amount=0, cash=None):
        o = book(customer, car, address, start, services)
        with frozen_now(start - timedelta(days=1)):
            confirm_with_payment(o, "cash", wallet_amount=wallet_amount)
        end = work_until_done_photos(o, self.tech, start)
        with frozen_now(end):
            o.refresh_from_db()
            complete_job(o, self.tech, cash_collected=o.amount_to_collect if cash is None else cash)
        return o

    def test_period_report(self):
        a, acar, aaddr = make_customer("01012345671")
        b, bcar, baddr = make_customer("01012345672")
        # a: an older order last month -> returning customer this month
        self.finish(a, acar, aaddr, cairo(WED - timedelta(days=28), 10))
        with frozen_now(cairo(WED - timedelta(days=3), 9)):
            wallet.credit(b, 5000, "manual", created_by=self.manager, note="x")
        o1 = self.finish(a, acar, aaddr, cairo(WED, 10))                               # 150, cash 150
        o2 = self.finish(b, bcar, baddr, cairo(WED, 13), wallet_amount=5000, cash=9000)  # 150 = 50 wallet + 90 cash (10 short)
        mat = Material.objects.create(name="شامبو", unit="liter", unit_cost=8000)
        record_materials(o1, self.tech, [{"material": mat.id, "quantity": "0.5"}])     # 40 EGP
        cancelled = book(a, acar, aaddr, cairo(WED, 17))
        with frozen_now(cairo(WED, 17) - timedelta(days=1)):
            confirm_with_payment(cancelled, "cash")
        with frozen_now(cairo(WED, 9)):
            cancel_by_customer(cancelled)  # free: more than 2 hours before

        r = self.c.get("/api/manage/reports/", {"from": WED.isoformat(), "to": WED.isoformat()}).json()
        t = r["totals"]
        self.assertEqual(t["orders"], 2)
        self.assertEqual((t["revenue"], t["collected"], t["wallet"], t["uncollected"]), (30000, 24000, 5000, 1000))
        self.assertEqual((t["materials"], t["margin"]), (4000, 26000))
        self.assertEqual(r["by_day"], [{"date": WED.isoformat(), "orders": 2, "revenue": 30000, "margin": 26000}])
        self.assertEqual(r["by_zone"][0]["name"], "مدينة نصر")
        self.assertEqual(r["by_service"], [{"name": "غسيل خارجي", "count": 2, "revenue": 30000}])
        self.assertEqual(r["customers"]["served"], 2)
        self.assertEqual((r["customers"]["returning"], r["customers"]["first_time"]), (1, 1))
        self.assertEqual(r["cancellations"]["by_customer"], 1)
        jt = r["job_times"][0]
        self.assertEqual((jt["service"], jt["size"], jt["count"], jt["planned"]), ("غسيل خارجي", "sedan", 2, 45))
        self.assertEqual(jt["actual_avg"], 45)  # the test technician starts and ends exactly on plan

    def test_bad_period_and_manager_only(self):
        self.assertEqual(self.c.get("/api/manage/reports/", {"from": "2026-11-20", "to": "2026-11-01"}).json()["code"], "bad_period")
        self.assertEqual(self.c.get("/api/manage/reports/", {"from": "x"}).json()["code"], "bad_date")
        self.assertEqual(self.c.get("/api/manage/reports/").status_code, 200)  # default: this month
        self.c.force_authenticate(User.objects.create_user("01012345678", "c"))
        self.assertEqual(self.c.get("/api/manage/reports/").status_code, 403)


@override_settings(MEDIA_ROOT=MEDIA)
class CustomersTests(TestCase):
    def test_list_search_profile_and_notes(self):
        manager = User.objects.create_user("01000000001", "Boss", role="manager")
        make_technician("01100000001")
        a, acar, aaddr = make_customer("01012345671")
        make_customer("01055555555")
        User.objects.filter(pk=a.pk).update(full_name="منى سمير")
        c = APIClient()
        c.force_authenticate(manager)
        self.assertEqual(len(c.get("/api/manage/customers/").json()), 2)
        self.assertEqual([x["name"] for x in c.get("/api/manage/customers/", {"search": "منى"}).json()], ["منى سمير"])
        self.assertEqual(len(c.get("/api/manage/customers/", {"search": "01055555555"}).json()), 1)
        book(a, acar, aaddr, cairo(WED, 10))
        p = c.get(f"/api/manage/customers/{a.id}/").json()
        self.assertEqual((p["name"], len(p["orders"]), p["wallet_balance"]), ("منى سمير", 1, 0))
        self.assertEqual(c.post(f"/api/manage/customers/{a.id}/notes/", {"text": ""}, format="json").status_code, 400)
        p = c.post(f"/api/manage/customers/{a.id}/notes/", {"text": "بتحب الفني محمود"}, format="json").json()
        self.assertEqual(p["notes"][0]["text"], "بتحب الفني محمود")
        c.force_authenticate(a)
        self.assertEqual(c.get(f"/api/manage/customers/{a.id}/").status_code, 403)
