from django.test import SimpleTestCase, TestCase

from core.models import Setting
from scheduling.travel import distance_km, get_travel_estimator, straight_line_minutes


class TravelMathTests(SimpleTestCase):
    def test_distance(self):
        self.assertAlmostEqual(distance_km((30.0, 31.0), (30.1, 31.0)), 11.12, places=2)  # 0.1 degree north
        self.assertEqual(distance_km((30.0, 31.0), (30.0, 31.0)), 0)

    def test_minutes(self):
        # 11.12 km x 1.4 = 15.57 km at 25 km/h = 37.4 min -> rounded UP to 38
        self.assertEqual(straight_line_minutes((30.0, 31.0), (30.1, 31.0), speed_kmh=25, road_factor_percent=140), 38)
        self.assertEqual(straight_line_minutes((30.0, 31.0), (30.0, 31.0), 25, 140), 0)
        # Faster speed, shorter time.
        self.assertEqual(straight_line_minutes((30.0, 31.0), (30.1, 31.0), 50, 140), 19)


class TravelSettingsTests(TestCase):
    def test_uses_settings(self):
        self.assertEqual(get_travel_estimator().minutes((30.0, 31.0), (30.1, 31.0)), 38)
        Setting.objects.filter(key="travel-speed-kmh").update(value=50)
        self.assertEqual(get_travel_estimator().minutes((30.0, 31.0), (30.1, 31.0)), 19)
        Setting.objects.filter(key="travel-road-factor-percent").update(value=100)
        self.assertEqual(get_travel_estimator().minutes((30.0, 31.0), (30.1, 31.0)), 14)  # 11.12/50*60=13.3
