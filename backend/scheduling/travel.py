"""Travel time between two places, in whole minutes (rounded up).

Until the Google Maps key arrives, it is estimated from the straight-line
distance: distance x road factor (140% = streets are not straight lines),
at an average speed (25 km/h in Cairo). Both numbers are settings.
Later a GoogleRoutesEstimator with the same minutes() method replaces it.
"""
import math

from core.services import get_setting

EARTH_RADIUS_KM = 6371.0


def distance_km(a, b):
    lat1, lng1 = map(math.radians, map(float, a))
    lat2, lng2 = map(math.radians, map(float, b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def straight_line_minutes(a, b, speed_kmh, road_factor_percent):
    km = distance_km(a, b) * road_factor_percent / 100
    return math.ceil(round(km / speed_kmh * 60, 6))


class StraightLineEstimator:
    def __init__(self, speed_kmh, road_factor_percent):
        self.speed_kmh = speed_kmh
        self.road_factor_percent = road_factor_percent

    def minutes(self, a, b):
        return straight_line_minutes(a, b, self.speed_kmh, self.road_factor_percent)


def get_travel_estimator():
    return StraightLineEstimator(get_setting("travel-speed-kmh"), get_setting("travel-road-factor-percent"))
