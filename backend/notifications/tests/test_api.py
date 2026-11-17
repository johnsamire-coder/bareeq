from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from notifications.models import DeviceToken, Notification
from notifications.service import notify


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("01012345678", "c")
        self.other = User.objects.create_user("01012345679", "o")
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_list_read_and_privacy(self):
        a = notify(self.user, "welcome", "أهلاً", "نص")
        notify(self.user, "wallet_credit", "رصيد", "نص")
        notify(self.other, "welcome", "أهلاً", "نص")
        r = self.c.get("/api/notifications/").json()
        self.assertEqual(r["unread"], 2)
        self.assertEqual([n["kind"] for n in r["results"]], ["wallet_credit", "welcome"])
        self.c.post(f"/api/notifications/{a.id}/read/")
        self.assertEqual(self.c.get("/api/notifications/").json()["unread"], 1)
        self.c.post("/api/notifications/read-all/")
        self.assertEqual(self.c.get("/api/notifications/").json()["unread"], 0)
        other_n = Notification.objects.get(user=self.other)
        self.assertEqual(self.c.post(f"/api/notifications/{other_n.id}/read/").status_code, 404)

    def test_register_device(self):
        r = self.c.post("/api/devices/", {"token": "abc", "platform": "android"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.c.post("/api/devices/", {"token": "abc", "platform": "android"}, format="json")  # same token again
        self.assertEqual(DeviceToken.objects.count(), 1)

    def test_dedupe_key(self):
        notify(self.user, "booking_reminder", "t", "b", dedupe_key="x")
        notify(self.user, "booking_reminder", "t", "b", dedupe_key="x")
        self.assertEqual(Notification.objects.count(), 1)
