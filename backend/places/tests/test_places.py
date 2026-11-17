from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from places.models import Address, AreaRequest, Zone
from places.services import find_zone

# Well-known spots (lat, lng)
CITY_STARS = (30.0729, 31.3456)       # Nasr City
OBOUR = (30.2280, 31.4800)
MADINATY = (30.1020, 31.6400)
TAHRIR = (30.0444, 31.2357)           # Downtown: outside
FIFTH_SETTLEMENT = (30.0074, 31.4913)  # New Cairo: outside
MAADI = (29.9602, 31.2569)            # outside


class SeedZonesTests(TestCase):
    def test_three_zones_seeded(self):
        self.assertEqual(list(Zone.objects.values_list("name", flat=True)), ["مدينة نصر", "العبور", "مدينتي"])

    def test_known_points(self):
        self.assertEqual(find_zone(*CITY_STARS).name, "مدينة نصر")
        self.assertEqual(find_zone(*OBOUR).name, "العبور")
        self.assertEqual(find_zone(*MADINATY).name, "مدينتي")
        for p in (TAHRIR, FIFTH_SETTLEMENT, MAADI):
            self.assertIsNone(find_zone(*p), p)

    def test_inactive_zone_ignored_and_overlap_uses_order(self):
        Zone.objects.filter(name="العبور").update(is_active=False)
        self.assertIsNone(find_zone(*OBOUR))
        big = Zone(name="كبيرة", polygon=[[29, 31], [31, 31], [31, 32], [29, 32]], sort_order=99)
        big.save()
        self.assertEqual(find_zone(*CITY_STARS).name, "مدينة نصر")  # lower order wins
        self.assertEqual(find_zone(*TAHRIR).name, "كبيرة")


class LocateApiTests(TestCase):
    def test_locate_public(self):
        c = APIClient()
        r = c.get("/api/zones-locate/", {"lat": MADINATY[0], "lng": MADINATY[1]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["zone"]["name"], "مدينتي")
        r = c.get("/api/zones-locate/", {"lat": TAHRIR[0], "lng": TAHRIR[1]})
        self.assertEqual(r.json(), {"covered": False, "zone": None})
        self.assertEqual(c.get("/api/zones-locate/", {"lat": 200, "lng": 1}).status_code, 400)


class AddressApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("01012345678", "Cust")
        self.other = User.objects.create_user("01012345679", "Other")
        self.client.force_authenticate(self.customer)

    def data(self, point=CITY_STARS, **over):
        d = {"label": "البيت", "lat": point[0], "lng": point[1], "building": "12", "floor": "3", "landmark": "جنب الجامع"}
        d.update(over)
        return d

    def test_add_address_gets_zone(self):
        r = self.client.post("/api/my-addresses/", self.data(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["zone"]["name"], "مدينة نصر")
        self.assertEqual(Address.objects.get().customer, self.customer)

    def test_outside_zone_rejected_with_code(self):
        r = self.client.post("/api/my-addresses/", self.data(TAHRIR), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "outside_service_area")
        self.assertFalse(Address.objects.exists())

    def test_required_fields(self):
        for missing in ("label", "building", "lat"):
            d = self.data()
            d.pop(missing)
            self.assertEqual(self.client.post("/api/my-addresses/", d, format="json").status_code, 400, missing)
        self.assertEqual(self.client.post("/api/my-addresses/", self.data(building="  "), format="json").status_code, 400)

    def test_moving_pin_updates_zone_or_is_rejected(self):
        aid = self.client.post("/api/my-addresses/", self.data(), format="json").json()["id"]
        r = self.client.patch(f"/api/my-addresses/{aid}/", {"lat": MADINATY[0], "lng": MADINATY[1]}, format="json")
        self.assertEqual(r.json()["zone"]["name"], "مدينتي")
        r = self.client.patch(f"/api/my-addresses/{aid}/", {"lat": MAADI[0], "lng": MAADI[1]}, format="json")
        self.assertEqual(r.json()["code"], "outside_service_area")
        self.assertEqual(Address.objects.get().zone.name, "مدينتي")

    def test_own_addresses_only_and_delete_hides(self):
        Address.objects.create(customer=self.other, label="x", lat=CITY_STARS[0], lng=CITY_STARS[1], building="1")
        aid = self.client.post("/api/my-addresses/", self.data(), format="json").json()["id"]
        self.assertEqual([a["id"] for a in self.client.get("/api/my-addresses/").json()], [aid])
        other_id = Address.objects.get(customer=self.other).id
        self.assertEqual(self.client.delete(f"/api/my-addresses/{other_id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/my-addresses/{aid}/").status_code, 204)
        self.assertEqual(self.client.get("/api/my-addresses/").json(), [])
        self.assertTrue(Address.objects.filter(pk=aid, is_active=False).exists())

    def test_customers_only(self):
        self.client.force_authenticate(User.objects.create_user("01000000003", "T", role="technician"))
        self.assertEqual(self.client.get("/api/my-addresses/").status_code, 403)

    def test_redrawing_zone_moves_saved_addresses(self):
        aid = self.client.post("/api/my-addresses/", self.data(), format="json").json()["id"]
        nasr = Zone.objects.get(name="مدينة نصر")
        nasr.polygon = [[30.0, 31.0], [30.01, 31.0], [30.01, 31.01]]  # moved away
        nasr.save()
        self.assertIsNone(Address.objects.get(pk=aid).zone)
        nasr.polygon = [[30.0, 31.3], [30.1, 31.3], [30.1, 31.4], [30.0, 31.4]]
        nasr.save()
        self.assertEqual(Address.objects.get(pk=aid).zone, nasr)


class ZoneApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer = User.objects.create_user("01012345678", "Cust")

    def test_customer_reads_active_only_and_cannot_edit(self):
        Zone.objects.filter(name="العبور").update(is_active=False)
        self.client.force_authenticate(self.customer)
        self.assertEqual([z["name"] for z in self.client.get("/api/zones/").json()], ["مدينة نصر", "مدينتي"])
        r = self.client.post("/api/zones/", {"name": "x", "polygon": [[0, 0], [0, 1], [1, 1]]}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_manager_creates_and_edits(self):
        self.client.force_authenticate(self.manager)
        self.assertEqual(len(self.client.get("/api/zones/").json()), 3)
        r = self.client.post("/api/zones/", {"name": "التجمع", "polygon": [[29.99, 31.45], [30.04, 31.45], [30.04, 31.52], [29.99, 31.52]]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(find_zone(*FIFTH_SETTLEMENT).name, "التجمع")
        r = self.client.post("/api/zones/", {"name": "غلط", "polygon": [[0, 0], [1, 1]]}, format="json")
        self.assertEqual(r.status_code, 400)
        zid = Zone.objects.get(name="التجمع").id
        self.assertEqual(self.client.patch(f"/api/zones/{zid}/", {"is_active": False}, format="json").status_code, 200)
        self.assertIsNone(find_zone(*FIFTH_SETTLEMENT))
        self.assertEqual(self.client.delete(f"/api/zones/{zid}/").status_code, 405)


class AreaRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("01012345678", "Cust")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")

    def test_notify_me_flow(self):
        self.client.force_authenticate(self.customer)
        r = self.client.post("/api/area-requests/", {"lat": FIFTH_SETTLEMENT[0], "lng": FIFTH_SETTLEMENT[1], "area_name": "التجمع"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        # Second request replaces the first (one open request per customer).
        r = self.client.post("/api/area-requests/", {"lat": MAADI[0], "lng": MAADI[1], "area_name": "المعادي"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AreaRequest.objects.count(), 1)
        self.assertEqual(AreaRequest.objects.get().area_name, "المعادي")
        # Customers cannot read the demand list.
        self.assertEqual(self.client.get("/api/area-requests/").status_code, 403)

        self.client.force_authenticate(self.manager)
        rows = self.client.get("/api/area-requests/").json()
        self.assertEqual(rows[0]["customer_phone"], "+201012345678")
        self.assertIsNone(rows[0]["now_covered_by"])
        Zone(name="المعادي", polygon=[[29.95, 31.24], [29.97, 31.24], [29.97, 31.27], [29.95, 31.27]]).save()
        self.assertEqual(self.client.get("/api/area-requests/").json()[0]["now_covered_by"], "المعادي")

    def test_inside_zone_refused(self):
        self.client.force_authenticate(self.customer)
        r = self.client.post("/api/area-requests/", {"lat": CITY_STARS[0], "lng": CITY_STARS[1]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "inside_service_area")
