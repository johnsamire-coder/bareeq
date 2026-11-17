from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import CarColor, CarModel, CustomerCar
from places.models import Address, Zone
from services.models import Service, ServicePrice

CITY_STARS = (30.0729, 31.3456)


def sid(code):
    return Service.objects.get(code=code).id


class CatalogAndQuoteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.nasr = Zone.objects.get(name="مدينة نصر")

    def test_catalog_by_zone_and_size_public(self):
        r = self.client.get("/api/services/catalog/", {"zone": self.nasr.id, "size_class": "suv"})
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(len(body["services"]), 8)
        ext = next(s for s in body["services"] if s["code"] == "exterior-wash")
        self.assertEqual((ext["price"], ext["minutes"]), (18000, 55))
        extd = next(s for s in body["services"] if s["code"] == "exterior-detailing")
        self.assertEqual(extd["replaces"], [sid("exterior-wash")])
        self.assertEqual([b["discount_percent"] for b in body["bundles"]], [10, 15])
        self.assertTrue(body["has_provisional_prices"])

    def test_catalog_hides_unpriced_services_and_bundles(self):
        ServicePrice.objects.filter(zone=self.nasr, service__code="engine-wash").delete()
        body = self.client.get("/api/services/catalog/", {"zone": self.nasr.id, "size_class": "sedan"}).json()
        self.assertNotIn("engine-wash", [s["code"] for s in body["services"]])
        self.assertEqual([b["discount_percent"] for b in body["bundles"]], [10])  # VIP needs engine wash

    def test_catalog_needs_zone_and_size(self):
        r = self.client.get("/api/services/catalog/", {"zone": self.nasr.id})
        self.assertEqual(r.json()["code"], "zone_and_size_required")

    def test_quote_by_zone(self):
        r = self.client.post("/api/services/quote/", {
            "zone": self.nasr.id, "size_class": "sedan",
            "services": [sid("exterior-wash"), sid("interior-wash")],
        }, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["total"], 24300)

    def test_quote_with_customer_car_and_address(self):
        customer = User.objects.create_user("01012345678", "Cust")
        model = CarModel.objects.get(brand__name_en="Toyota", name="Corolla")  # sedan
        car = CustomerCar.objects.create(customer=customer, brand=model.brand, model=model, year=2020,
                                         color=CarColor.objects.first(), parking="street")
        addr = Address.objects.create(customer=customer, label="البيت", lat=CITY_STARS[0], lng=CITY_STARS[1],
                                      building="1", zone=self.nasr)
        data = {"address": addr.id, "car": car.id, "services": [sid("polish-protection")]}
        self.assertEqual(self.client.post("/api/services/quote/", data, format="json").status_code, 401)
        self.client.force_authenticate(customer)
        r = self.client.post("/api/services/quote/", data, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["total"], 150000)
        self.assertEqual(len(r.json()["warnings"]), 1)  # street + needs shade
        # Someone else's car is refused.
        other = User.objects.create_user("01012345679", "Other")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post("/api/services/quote/", data, format="json").status_code, 400)


class ManagerApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer = User.objects.create_user("01012345678", "Cust")

    def test_customer_cannot_manage(self):
        self.client.force_authenticate(self.customer)
        for url in ("/api/manage/services/", "/api/manage/service-prices/", "/api/manage/bundles/"):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_edit_price_clears_provisional(self):
        self.client.force_authenticate(self.manager)
        nasr = Zone.objects.get(name="مدينة نصر")
        rows = self.client.get("/api/manage/service-prices/", {"zone": nasr.id, "service": sid("exterior-wash")}).json()
        self.assertEqual(len(rows), 4)
        row = next(r for r in rows if r["size_class"] == "sedan")
        r = self.client.patch(f"/api/manage/service-prices/{row['id']}/", {"price": 17500, "zone": Zone.objects.get(name="العبور").id}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        p = ServicePrice.objects.get(pk=row["id"])
        self.assertEqual((p.price, p.is_provisional, p.zone_id), (17500, False, nasr.id))
        self.assertEqual(self.client.patch(f"/api/manage/service-prices/{row['id']}/", {"price": 10.5}, format="json").status_code, 400)

    def test_confirm_all(self):
        self.client.force_authenticate(self.manager)
        r = self.client.post("/api/manage/service-prices/confirm-all/")
        self.assertEqual(r.json()["confirmed"], 96)
        self.assertFalse(ServicePrice.objects.filter(is_provisional=True).exists())

    def test_durations_bundles_and_no_delete(self):
        self.client.force_authenticate(self.manager)
        d = self.client.get("/api/manage/service-durations/").json()[0]
        self.assertEqual(self.client.patch(f"/api/manage/service-durations/{d['id']}/", {"minutes": 0}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/manage/service-durations/{d['id']}/", {"minutes": 50}, format="json").status_code, 200)
        r = self.client.post("/api/manage/bundles/", {"name": "x", "services": [sid("engine-wash")], "discount_percent": 5}, format="json")
        self.assertEqual(r.status_code, 400)  # needs 2 services
        r = self.client.post("/api/manage/bundles/", {"name": "x", "services": [sid("engine-wash"), sid("oil-change")], "discount_percent": 101}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/manage/services/{sid('engine-wash')}/").status_code, 405)

    def test_service_cannot_replace_itself(self):
        self.client.force_authenticate(self.manager)
        s = sid("engine-wash")
        r = self.client.patch(f"/api/manage/services/{s}/", {"replaces": [s]}, format="json")
        self.assertEqual(r.status_code, 400)


class AdminPagesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("01000000009", "Admin", password="pw-For-Test-1")
        self.client.force_login(self.admin)

    def test_provisional_warning_and_pounds_form(self):
        r = self.client.get("/admin/services/serviceprice/")
        self.assertContains(r, "96 سعر لسه مؤقت")
        p = ServicePrice.objects.get(zone__name="مدينة نصر", service__code="exterior-wash", size_class="sedan")
        r = self.client.get(f"/admin/services/serviceprice/{p.id}/change/")
        self.assertContains(r, 'value="150')
        r = self.client.post(f"/admin/services/serviceprice/{p.id}/change/", {
            "service": p.service_id, "zone": p.zone_id, "size_class": "sedan", "price_pounds": "162.50",
        })
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual((p.price, p.is_provisional), (16250, False))
