from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from cars.models import CarColor, CarModel, CustomerCar


class InboxTests(TestCase):
    def test_counts_and_manager_only(self):
        manager = User.objects.create_user("01000000001", "Boss", role="manager")
        customer = User.objects.create_user("01012345678", "c")
        m = CarModel.objects.get(brand__name_en="Kia", name="Rio")
        CustomerCar.objects.create(customer=customer, brand=m.brand, unlisted_model_name="EV9", size_class="suv",
                                   year=2024, color=CarColor.objects.first(), parking="street")
        c = APIClient()
        c.force_authenticate(customer)
        self.assertEqual(c.get("/api/manage/inbox/").status_code, 403)
        c.force_authenticate(manager)
        r = c.get("/api/manage/inbox/").json()
        self.assertEqual(r["car_models_to_review"], 1)
        self.assertEqual(r["instapay_to_review"], 0)
        self.assertEqual(set(r), {"instapay_to_review", "refunds_due", "closings_to_confirm", "bad_ratings",
                                  "damage_reports", "car_models_to_review", "notify_me_requests", "orders_today"})
