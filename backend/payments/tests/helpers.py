import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile

from orders.booking import create_order
from orders.lifecycle import arrived, on_the_way, start_job
from orders.photos import add_photo
from orders.tests.helpers import CITY_STARS, cairo, frozen_now, jpeg_bytes, sid

MEDIA = tempfile.mkdtemp()
SIDES = ["front", "back", "left", "right"]


def book(customer, car, address, start, services=("exterior-wash", "interior-wash")):
    with frozen_now(start - timedelta(days=1)):
        return create_order(customer, address.id, [{"car": car.id, "services": sid(*services)}], start)


def proof():
    return SimpleUploadedFile("proof.jpg", jpeg_bytes(size=(600, 1200)), content_type="image/jpeg")


def work_until_done_photos(order, tech, start):
    """Technician goes, arrives, shoots 4+4 photos and starts. Leaves the job in progress
    with the 'after' photos taken, ready for complete_job."""
    with frozen_now(start - timedelta(minutes=20)):
        on_the_way(order, tech)
    with frozen_now(start):
        arrived(order, tech)
        for side in SIDES:
            add_photo(order, tech, "before", side, jpeg_bytes(size=(200, 150)), start, *CITY_STARS)
        start_job(order, tech)
    end = start + timedelta(minutes=order.total_minutes)
    with frozen_now(end):
        for side in SIDES:
            add_photo(order, tech, "after", side, jpeg_bytes(size=(200, 150)), end, *CITY_STARS)
    return end
