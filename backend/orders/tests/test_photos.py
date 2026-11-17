"""Before/after photos are evidence: resized to 1600 px, with the time and
place they were taken, the upload time, and a fingerprint of the original
file. Photos taken long before upload or far from the address are flagged."""
from datetime import timedelta

from django.test import TestCase, override_settings

from core.errors import BusinessError
from orders.lifecycle import arrived, on_the_way
from orders.models import OrderPhoto
from orders.photos import add_photo

from .helpers import CITY_STARS, WED, book_confirmed, cairo, frozen_now, jpeg_bytes, make_customer, make_technician

import tempfile

TMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PhotoTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.customer, self.car, self.address = make_customer()
        self.order = book_confirmed(self.customer, self.car, self.address, cairo(WED, 14))
        with frozen_now(cairo(WED, 13, 40)):
            on_the_way(self.order, self.tech)
        with frozen_now(cairo(WED, 14)):
            arrived(self.order, self.tech)

    def add(self, now=cairo(WED, 14, 2), captured=cairo(WED, 14, 1), point=CITY_STARS, data=None, **kw):
        with frozen_now(now):
            return add_photo(self.order, self.tech, kw.get("stage", "before"), kw.get("side", "front"),
                             data or jpeg_bytes(), captured_at=captured, lat=point[0], lng=point[1], accuracy_m=10)

    def test_resized_and_recorded(self):
        p = self.add()
        self.assertEqual((p.width, p.height), (1600, 1067))
        self.assertEqual(p.captured_at, cairo(WED, 14, 1))
        self.assertEqual(p.uploaded_at, cairo(WED, 14, 2))
        self.assertEqual((float(p.lat), float(p.lng), p.accuracy_m), (CITY_STARS[0], CITY_STARS[1], 10))
        self.assertEqual(len(p.original_sha256), 64)
        self.assertEqual(p.taken_by, self.tech)
        self.assertEqual(p.flags, [])
        self.assertTrue(p.image.name.endswith(".jpg"))

    def test_small_photo_not_enlarged(self):
        p = self.add(data=jpeg_bytes(size=(800, 600)))
        self.assertEqual((p.width, p.height), (800, 600))

    def test_old_photo_flagged(self):
        p = self.add(captured=cairo(WED, 13, 30))  # 32 minutes before upload
        self.assertIn("taken_long_before_upload", p.flags)

    def test_far_photo_flagged(self):
        p = self.add(point=(30.1020, 31.6400))  # Madinaty, far from the Nasr City address
        self.assertIn("far_from_address", p.flags)

    def test_retake_keeps_old_photo(self):
        self.add()
        self.add()
        self.assertEqual(OrderPhoto.objects.filter(stage="before", side="front").count(), 2)

    def test_rejects_non_images_and_missing_data(self):
        with self.assertRaises(BusinessError):
            self.add(data=b"not an image")
        with self.assertRaises(BusinessError):
            with frozen_now(cairo(WED, 14, 2)):
                add_photo(self.order, self.tech, "before", "front", jpeg_bytes(), captured_at=None, lat=None, lng=None)
        with self.assertRaises(BusinessError):
            self.add(side="roof")

    def test_after_photos_only_while_working(self):
        with self.assertRaises(BusinessError):
            self.add(stage="after")
