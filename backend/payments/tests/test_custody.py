"""Technician custody (عهدة): when a technician hands over less cash than he
collected, the shortage is recorded on him; when he hands over more, the
overage is recorded too. The manager cannot confirm a closing with a
difference without writing the reason. Settlements reduce the custody.
Rows are never edited or deleted."""
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from core.errors import BusinessError
from orders.lifecycle import complete_job
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments.closing import confirm_closing, submit_closing
from payments.custody import custody_report, settle_custody
from payments.models import TechnicianCustody
from payments.payments import confirm_with_payment

from .helpers import MEDIA, book, work_until_done_photos

THU = WED + timedelta(days=1)


@override_settings(MEDIA_ROOT=MEDIA)
class CustodyTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()

    def cash_day(self, day, collected):
        """One completed cash job on `day`; the technician collects `collected` piastres."""
        start = cairo(day, 10)
        o = book(self.customer, self.car, self.address, start)
        with frozen_now(start - timedelta(days=1)):
            confirm_with_payment(o, "cash")
        end = work_until_done_photos(o, self.tech, start)
        with frozen_now(end):
            complete_job(o, self.tech, cash_collected=collected)

    def close(self, day, handed):
        with frozen_now(cairo(day, 22)):
            return submit_closing(self.tech, day, cash_handed=handed)

    def test_shortage_needs_reason_and_becomes_custody(self):
        self.cash_day(WED, 24300)
        c = self.close(WED, 24000)  # 3 EGP short
        with self.assertRaises(BusinessError) as e:
            confirm_closing(c, self.manager)
        self.assertEqual(e.exception.detail["code"], "reason_required")
        with self.assertRaises(BusinessError):
            confirm_closing(c, self.manager, reason="   ")
        confirm_closing(c, self.manager, reason="الفني قال الفكة مكانتش معاه")
        c.refresh_from_db()
        self.assertEqual((c.status, c.confirm_reason), ("confirmed", "الفني قال الفكة مكانتش معاه"))
        row = TechnicianCustody.objects.get()
        self.assertEqual((row.kind, row.amount, row.technician, row.closing, row.created_by),
                         ("shortage", 300, self.tech, c, self.manager))

    def test_overage_recorded_too(self):
        self.cash_day(WED, 24300)
        c = self.close(WED, 25000)  # 7 EGP extra
        confirm_closing(c, self.manager, reason="العميل ساب الباقي")
        row = TechnicianCustody.objects.get()
        self.assertEqual((row.kind, row.amount), ("overage", 700))

    def test_no_difference_no_reason_no_row(self):
        self.cash_day(WED, 24300)
        confirm_closing(self.close(WED, 24300), self.manager)
        self.assertFalse(TechnicianCustody.objects.exists())

    def test_report_and_settlement(self):
        self.cash_day(WED, 24300)
        confirm_closing(self.close(WED, 23300), self.manager, reason="ناقص 10")    # -10
        self.cash_day(THU, 24300)
        confirm_closing(self.close(THU, 24800), self.manager, reason="زيادة 5")    # +5
        r = custody_report()
        row = next(x for x in r if x["technician"] == self.tech.id)
        self.assertEqual((row["shortages"], row["overages"], row["settled"], row["balance"]), (1000, 500, 0, 500))
        with self.assertRaises(BusinessError):
            settle_custody(self.tech, 600, self.manager, "دفع")  # more than he owes
        with self.assertRaises(BusinessError):
            settle_custody(self.tech, 300, self.manager, "")     # reason required
        settle_custody(self.tech, 500, self.manager, "اتخصم من المرتب")
        row = next(x for x in custody_report() if x["technician"] == self.tech.id)
        self.assertEqual((row["settled"], row["balance"]), (500, 0))

    def test_rows_are_never_edited_or_deleted(self):
        self.cash_day(WED, 24300)
        confirm_closing(self.close(WED, 24000), self.manager, reason="x")
        row = TechnicianCustody.objects.get()
        row.amount = 1
        with self.assertRaises(ValueError):
            row.save()
        with self.assertRaises(ValueError):
            row.delete()

    def test_api(self):
        self.cash_day(WED, 24300)
        c = self.close(WED, 24000)
        api = APIClient()
        api.force_authenticate(self.manager)
        r = api.post(f"/api/manage/daily-closings/{c.id}/confirm/", {}, format="json")
        self.assertEqual(r.json()["code"], "reason_required")
        r = api.post(f"/api/manage/daily-closings/{c.id}/confirm/", {"reason": "فكة"}, format="json")
        self.assertEqual(r.json()["status"], "confirmed")
        rows = api.get("/api/manage/technician-custody/").json()
        mine = next(x for x in rows if x["technician"] == self.tech.id)
        self.assertEqual(mine["balance"], 300)
        r = api.post("/api/manage/technician-custody/settle/", {"technician": self.tech.id, "amount": 300, "reason": "دفعها كاش"},
                     format="json")
        self.assertEqual(r.status_code, 201, r.content)
        entries = api.get("/api/manage/technician-custody/", {"technician": self.tech.id}).json()
        self.assertEqual([e["kind"] for e in entries["entries"]], ["settlement", "shortage"])
        # The technician sees what is on him in his closing screen.
        api.force_authenticate(self.tech)
        self.assertEqual(api.get("/api/technician/closing/", {"date": WED.isoformat()}).json()["custody_balance"], 0)
        api.force_authenticate(self.customer)
        self.assertEqual(api.get("/api/manage/technician-custody/").status_code, 403)
