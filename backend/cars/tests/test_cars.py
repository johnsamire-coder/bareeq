from datetime import date
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from cars.catalog_seed import CATALOG, COLORS
from cars.models import CarBrand, CarColor, CarModel, CustomerCar, allowed_years
from core.models import Setting


class CatalogSeedTests(TestCase):
    def test_catalog_seeded(self):
        self.assertEqual(CarBrand.objects.count(), len(CATALOG))
        self.assertEqual(CarModel.objects.count(), sum(len(m) for *_, m in CATALOG))
        self.assertEqual(CarColor.objects.count(), len(COLORS))

    def test_chinese_brands_present(self):
        for name in ("Chery", "MG", "Geely", "BYD", "Jetour", "Haval", "Changan"):
            self.assertTrue(CarBrand.objects.filter(name_en=name).exists(), name)

    def test_every_model_has_a_size(self):
        self.assertFalse(CarModel.objects.exclude(size_class__in=["hatchback", "sedan", "suv", "luxury"]).exists())

    def test_sample_sizes(self):
        def size(brand, model):
            return CarModel.objects.get(brand__name_en=brand, name=model).size_class

        self.assertEqual(size("Hyundai", "Elantra"), "sedan")
        self.assertEqual(size("Kia", "Picanto"), "hatchback")
        self.assertEqual(size("Chery", "Tiggo 7"), "suv")
        self.assertEqual(size("Mercedes-Benz", "C-Class"), "luxury")


class YearsTests(TestCase):
    def test_default_range_1990_to_next_year(self):
        with mock.patch("django.utils.timezone.localdate", return_value=date(2026, 11, 17)):
            years = allowed_years()
        self.assertEqual(years[0], 2027)
        self.assertEqual(years[-1], 1990)
        self.assertEqual(len(years), 2027 - 1990 + 1)

    def test_range_is_a_setting(self):
        Setting.objects.filter(key="cars-first-year").update(value=2000)
        Setting.objects.filter(key="cars-years-ahead").update(value=0)
        with mock.patch("django.utils.timezone.localdate", return_value=date(2026, 11, 17)):
            years = allowed_years()
        self.assertEqual((years[0], years[-1]), (2026, 2000))


class MyCarsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("01012345678", "Cust")
        self.other = User.objects.create_user("01012345679", "Other")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.tech = User.objects.create_user("01000000002", "Tech", role="technician")
        self.brand = CarBrand.objects.get(name_en="Hyundai")
        self.model = CarModel.objects.get(brand=self.brand, name="Tucson")
        self.color = CarColor.objects.first()
        self.client.force_authenticate(self.customer)

    def car_data(self, **over):
        d = {"brand": self.brand.id, "model": self.model.id, "year": 2020, "color": self.color.id, "parking": "street"}
        d.update(over)
        return d

    def test_add_car_size_comes_from_catalog(self):
        r = self.client.post("/api/my-cars/", self.car_data(size_class="hatchback", plate_number="أ ب ج 123"), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        car = CustomerCar.objects.get()
        self.assertEqual(car.size_class, "suv")  # ignores what the app sent
        self.assertFalse(car.needs_review)
        self.assertEqual(car.customer, self.customer)
        self.assertEqual(r.json()["display_name"], "Hyundai Tucson 2020")

    def test_validation(self):
        other_brand_model = CarModel.objects.get(brand__name_en="Kia", name="Rio")
        cases = [
            self.car_data(model=other_brand_model.id),
            self.car_data(year=1989),
            self.car_data(year=2100),
            self.car_data(model=None),  # no model and no unlisted name
            self.car_data(parking="roof"),
        ]
        for data in cases:
            r = self.client.post("/api/my-cars/", data, format="json")
            self.assertEqual(r.status_code, 400, data)
        self.assertFalse(CustomerCar.objects.exists())

    def test_unlisted_model_needs_size_and_goes_to_review(self):
        r = self.client.post("/api/my-cars/", self.car_data(model=None, unlisted_model_name="Staria"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("size_class", r.json())
        r = self.client.post(
            "/api/my-cars/", self.car_data(model=None, unlisted_model_name="Staria", size_class="suv"), format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.json()["needs_review"])
        self.assertEqual(r.json()["display_name"], "Hyundai Staria 2020")

    def test_customer_sees_only_own_cars_and_delete_hides(self):
        CustomerCar.objects.create(customer=self.other, brand=self.brand, model=self.model, year=2020,
                                   color=self.color, parking="street")
        r = self.client.post("/api/my-cars/", self.car_data(), format="json")
        mine = r.json()["id"]
        self.assertEqual([c["id"] for c in self.client.get("/api/my-cars/").json()], [mine])
        self.assertEqual(self.client.delete(f"/api/my-cars/{mine}/").status_code, 204)
        self.assertEqual(self.client.get("/api/my-cars/").json(), [])
        self.assertTrue(CustomerCar.objects.filter(pk=mine, is_active=False).exists())

    def test_cannot_touch_other_customers_car(self):
        car = CustomerCar.objects.create(customer=self.other, brand=self.brand, model=self.model, year=2020,
                                         color=self.color, parking="street")
        self.assertEqual(self.client.patch(f"/api/my-cars/{car.id}/", {"plate_number": "x"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/my-cars/{car.id}/").status_code, 404)

    def test_edit_car(self):
        car_id = self.client.post("/api/my-cars/", self.car_data(), format="json").json()["id"]
        r = self.client.patch(f"/api/my-cars/{car_id}/", {"parking": "closed_garage", "plate_number": "123"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(CustomerCar.objects.get().parking, "closed_garage")

    def test_old_car_still_editable_after_year_range_narrowed(self):
        car_id = self.client.post("/api/my-cars/", self.car_data(year=1995), format="json").json()["id"]
        Setting.objects.filter(key="cars-first-year").update(value=2000)
        r = self.client.patch(f"/api/my-cars/{car_id}/", {"plate_number": "123"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_only_customers_have_my_cars(self):
        for u in (self.tech, self.manager):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.get("/api/my-cars/").status_code, 403)

    def test_hidden_model_cannot_be_chosen(self):
        self.model.is_active = False
        self.model.save()
        self.assertEqual(self.client.post("/api/my-cars/", self.car_data(), format="json").status_code, 400)


class CatalogApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("01012345678", "Cust")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")

    def test_search_brands_arabic_and_english(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual([b["name_en"] for b in self.client.get("/api/car-brands/?search=شيري").json()], ["Chery"])
        self.assertEqual([b["name_en"] for b in self.client.get("/api/car-brands/?search=byd").json()], ["BYD"])

    def test_models_by_brand_and_search(self):
        self.client.force_authenticate(self.customer)
        chery = CarBrand.objects.get(name_en="Chery")
        names = [m["name"] for m in self.client.get(f"/api/car-models/?brand={chery.id}&search=tiggo 7").json()]
        self.assertEqual(sorted(names), ["Tiggo 7", "Tiggo 7 Pro"])

    def test_hidden_brand_not_shown_to_customer_but_shown_to_manager(self):
        CarBrand.objects.filter(name_en="Lada").update(is_active=False)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/car-brands/?search=lada").json(), [])
        self.client.force_authenticate(self.manager)
        self.assertEqual(len(self.client.get("/api/car-brands/?search=lada").json()), 1)

    def test_only_manager_edits_catalog(self):
        brand = CarBrand.objects.get(name_en="Kia")
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post("/api/car-models/", {"brand": brand.id, "name": "EV6", "size_class": "suv"}).status_code, 403)
        self.client.force_authenticate(self.manager)
        r = self.client.post("/api/car-models/", {"brand": brand.id, "name": "EV6", "size_class": "suv"}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.client.post("/api/car-models/", {"brand": brand.id, "name": "ev6", "size_class": "suv"}, format="json")
        self.assertEqual(r.status_code, 400)  # duplicate
        rio = CarModel.objects.get(brand=brand, name="Rio")
        r = self.client.patch(f"/api/car-models/{rio.id}/", {"size_class": "sedan"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.delete(f"/api/car-models/{rio.id}/").status_code, 405)

    def test_car_options(self):
        self.client.force_authenticate(self.customer)
        r = self.client.get("/api/car-options/").json()
        self.assertEqual(r["years"][-1], 1990)
        self.assertEqual([p["value"] for p in r["parking"]], ["closed_garage", "open_garage", "street"])
        self.assertEqual(len(self.client.get("/api/car-colors/").json()), len(COLORS))


class UnlistedReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.brand = CarBrand.objects.get(name_en="Hyundai")
        color = CarColor.objects.first()
        self.cars = [
            CustomerCar.objects.create(
                customer=User.objects.create_user(f"0101234567{i}", "c"), brand=self.brand,
                unlisted_model_name=name, size_class="sedan", year=2020, color=color, parking="street",
            )
            for i, name in enumerate(["Staria", "staria", "Ioniq"])
        ]
        self.client.force_authenticate(self.manager)

    def test_review_list_and_add_new_model_links_all_same_name(self):
        self.assertEqual(len(self.client.get("/api/unlisted-cars/").json()), 3)
        r = self.client.post(
            f"/api/unlisted-cars/{self.cars[0].id}/review/", {"new_model_name": "Staria", "size_class": "suv"}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["cars_linked"], 2)
        for c in self.cars[:2]:
            c.refresh_from_db()
            self.assertEqual((c.model.name, c.size_class, c.needs_review), ("Staria", "suv", False))
        self.assertEqual(len(self.client.get("/api/unlisted-cars/").json()), 1)

    def test_link_to_existing_model(self):
        tucson = CarModel.objects.get(brand=self.brand, name="Tucson")
        r = self.client.post(f"/api/unlisted-cars/{self.cars[2].id}/review/", {"model": tucson.id}, format="json")
        self.assertEqual(r.status_code, 200)
        self.cars[2].refresh_from_db()
        self.assertEqual((self.cars[2].model, self.cars[2].size_class), (tucson, "suv"))

    def test_link_to_other_brand_rejected(self):
        rio = CarModel.objects.get(brand__name_en="Kia", name="Rio")
        r = self.client.post(f"/api/unlisted-cars/{self.cars[2].id}/review/", {"model": rio.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.cars[2].refresh_from_db()
        self.assertTrue(self.cars[2].needs_review)

    def test_customer_cannot_review(self):
        self.client.force_authenticate(self.cars[0].customer)
        self.assertEqual(self.client.get("/api/unlisted-cars/").status_code, 403)
