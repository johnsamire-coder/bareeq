"""The whole phase-4 journey through the API: the manager adds a supervisor ->
a customer far from the technicians asks «عايز حد دلوقتي» (express + distance
fees shown before booking) -> pays cash -> the technician goes and his app
sends his position -> the customer follows him on the map -> the supervisor
sees him on the day's map -> the job is done -> the detailed report and Excel."""
import io
from datetime import timedelta

from django.test import TestCase, override_settings
from openpyxl import load_workbook
from rest_framework.test import APIClient

from accounts.models import User
from orders.tests.helpers import CITY_STARS, WED, cairo, frozen_now, make_customer, make_technician, sid
from payments.tests.helpers import MEDIA
from places.models import Address, Zone

NOW = cairo(WED, 10, 2)


@override_settings(MEDIA_ROOT=MEDIA)
class PhaseFourJourneyTests(TestCase):
    def test_full_phase_four_journey(self):
        tech = make_technician("01100000001")
        manager = User.objects.create_user("01000000001", "المدير", role="manager")
        customer, car, _ = make_customer()
        far = Address.objects.create(customer=customer, label="الشغل", lat=30.19, lng=CITY_STARS[1], building="7",
                                     zone=Zone.objects.get(name="مدينة نصر"))
        cust, mgr, sup, techc = APIClient(), APIClient(), APIClient(), APIClient()
        cust.force_authenticate(customer)
        mgr.force_authenticate(manager)
        techc.force_authenticate(tech)
        items = [{"car": car.id, "services": sid("exterior-wash", "interior-wash")}]

        with frozen_now(NOW):
            # 1. The manager adds a supervisor for Nasr City.
            r = mgr.post("/api/manage/supervisors/", {"full_name": "مشرف", "phone": "01200000001",
                                                      "zones": [far.zone_id]}, format="json")
            sup.force_authenticate(User.objects.get(pk=r.json()["id"]))

            # 2. Express + distance fee are shown before booking.
            s = cust.post("/api/booking/slots/", {"address": far.id, "items": items}, format="json").json()
            self.assertEqual((s["distance_fee"], s["express"]["fee"]), (2000, 5000))
            e = cust.post("/api/booking/express/", {"address": far.id, "items": items}, format="json").json()
            self.assertTrue(e["available"])
            o = cust.post("/api/orders/", {"address": far.id, "items": items, "start": e["start"], "express": True},
                          format="json").json()
            self.assertEqual(o["amount_due"], 24300 + 5000 + 2000)
            o = cust.post(f"/api/orders/{o['id']}/confirm/", {"payment_method": "cash"}, format="json").json()
            oid = o["id"]

            # 3. The technician goes; his app sends his position; the customer follows.
            self.assertFalse(techc.post("/api/technician/location/", {}, format="json").json()["active"])
            techc.post(f"/api/technician/jobs/{oid}/on-the-way/")
            self.assertTrue(techc.post("/api/technician/location/", {"lat": "30.120000", "lng": "31.345600"},
                                       format="json").json()["active"])
            t = cust.get(f"/api/orders/{oid}/tracking/").json()
            self.assertEqual((t["active"], t["lat"]), (True, 30.12))

            # 4. The supervisor sees it on the day's map.
            m = sup.get("/api/manage/live-map/").json()
            self.assertEqual(m["technicians"][0]["on_the_way_to"], oid)
            self.assertTrue(m["orders"][0]["is_express"])

        # 5. The job is done (cash collected).
        from orders.lifecycle import arrived
        from orders.models import Order

        order = Order.objects.get(pk=oid)
        with frozen_now(order.scheduled_start):
            arrived(order, tech)
        from orders.lifecycle import start_job
        from orders.photos import add_photo
        from orders.tests.helpers import jpeg_bytes

        with frozen_now(order.scheduled_start):
            for side in ("front", "back", "left", "right"):
                add_photo(order, tech, "before", side, jpeg_bytes(size=(200, 150)), order.scheduled_start, 30.19,
                          CITY_STARS[1])
            start_job(order, tech)
        end = order.scheduled_start + timedelta(minutes=order.total_minutes)
        with frozen_now(end):
            for side in ("front", "back", "left", "right"):
                add_photo(order, tech, "after", side, jpeg_bytes(size=(200, 150)), end, 30.19, CITY_STARS[1])
            r = techc.post(f"/api/technician/jobs/{oid}/complete/", {"cash_collected": 31300}, format="json")
            self.assertEqual(r.json()["status"], "completed", r.content)
            self.assertFalse(cust.get(f"/api/orders/{oid}/tracking/").json()["active"])

            # 6. Detailed report and Excel.
            q = {"from": WED.isoformat(), "to": WED.isoformat()}
            row = mgr.get("/api/manage/reports/technicians/", q).json()["rows"][0]
            self.assertEqual((row["completed"], row["express"], row["revenue"], row["on_time_percent"]),
                             (1, 1, 31300, 100))
            z = mgr.get("/api/manage/reports/zones/", q).json()["rows"][0]
            self.assertEqual((z["distance_fees"], z["express"]), (2000, 1))
            url = mgr.post("/api/manage/reports/export/", {"report": "technicians", **q}, format="json").json()["url"]
            wb = load_workbook(io.BytesIO(self.client.get(url.split("testserver")[1]).content))
            self.assertEqual(wb.worksheets[0]["A2"].value, "فني 01")
