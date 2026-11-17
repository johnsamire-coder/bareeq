from datetime import datetime, time
from unittest import mock
from zoneinfo import ZoneInfo

from accounts.models import User
from cars.models import CarColor, CarModel, CustomerCar
from places.models import Address, Zone
from scheduling.models import WeeklyShift
from services.models import Service

CAIRO = ZoneInfo("Africa/Cairo")
CITY_STARS = (30.0729, 31.3456)  # Nasr City
WED = datetime(2026, 11, 18).date()  # a Wednesday


def cairo(day, h, m=0):
    return datetime.combine(day, time(h, m), tzinfo=CAIRO)


def frozen_now(dt):
    return mock.patch("django.utils.timezone.now", return_value=dt)


def sid(*codes):
    by = dict(Service.objects.values_list("code", "id"))
    return [by[c] for c in codes]


def make_technician(phone, zones=("مدينة نصر",), home=CITY_STARS, weekdays=range(7), hours=(9, 22)):
    user = User.objects.create_user(phone, f"فني {phone[-2:]}", role="technician")
    profile = user.technician_profile
    profile.zones.set(Zone.objects.filter(name__in=zones))
    profile.start_lat, profile.start_lng = home
    profile.save()
    for wd in weekdays:
        WeeklyShift.objects.create(technician=profile, weekday=wd, start_time=time(hours[0]), end_time=time(hours[1]))
    return user


def make_customer(phone="01012345678", point=CITY_STARS, model=("Toyota", "Corolla")):
    customer = User.objects.create_user(phone, "عميل")
    m = CarModel.objects.get(brand__name_en=model[0], name=model[1])
    car = CustomerCar.objects.create(customer=customer, brand=m.brand, model=m, year=2020,
                                     color=CarColor.objects.first(), parking="closed_garage")
    address = Address.objects.create(customer=customer, label="البيت", lat=point[0], lng=point[1], building="1",
                                     zone=Zone.objects.get(name="مدينة نصر"))
    return customer, car, address


def jpeg_bytes(size=(3000, 2000), color=(200, 30, 30)):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


def book_confirmed(customer, car, address, start, services=("exterior-wash",), now=None):
    from orders.booking import confirm_order, create_order

    with frozen_now(now or start - __import__("datetime").timedelta(days=1)):
        o = create_order(customer, address.id, [{"car": car.id, "services": sid(*services)}], start)
        return confirm_order(o, "cash")
