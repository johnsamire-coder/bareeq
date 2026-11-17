from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from core.defaults import DEFAULT_SETTINGS, seed_default_settings
from core.models import Setting
from core.services import SettingMissing, get_setting


class DefaultSettingsTests(TestCase):
    def test_all_defaults_seeded_by_migration(self):
        keys = set(Setting.objects.values_list("key", flat=True))
        self.assertEqual(keys, {s["key"] for s in DEFAULT_SETTINGS})

    def test_spec_values(self):
        self.assertEqual(get_setting("scheduling-buffer-minutes"), 15)
        self.assertEqual(get_setting("scheduling-min-gap-minutes"), 90)
        self.assertEqual(get_setting("scheduling-slot-hold-minutes"), 10)
        self.assertEqual(get_setting("wallet-max-order-share-percent"), 50)
        self.assertEqual(get_setting("wallet-credit-expiry-days"), 90)

    def test_reseeding_never_overwrites_manager_edits(self):
        s = Setting.objects.get(key="scheduling-buffer-minutes")
        s.value = 20
        s.save()
        self.assertEqual(seed_default_settings(Setting), 0)
        self.assertEqual(get_setting("scheduling-buffer-minutes"), 20)

    def test_missing_setting_raises(self):
        with self.assertRaises(SettingMissing):
            get_setting("does-not-exist")


class SettingValidationTests(TestCase):
    def make(self, value_type, value):
        return Setting(key="t", group="g", label="t", value_type=value_type, value=value)

    def test_rejects_float_money(self):
        with self.assertRaises(ValidationError):
            self.make("money", 10.5).save()

    def test_rejects_negative_and_bool_numbers(self):
        for bad in (-1, True, "15"):
            with self.assertRaises(ValidationError):
                self.make("minutes", bad).save()

    def test_percent_range(self):
        with self.assertRaises(ValidationError):
            self.make("percent", 101).save()
        self.make("percent", 100).save()

    def test_boolean_and_text(self):
        with self.assertRaises(ValidationError):
            self.make("boolean", 1).save()
        with self.assertRaises(ValidationError):
            self.make("text", 5).save()


class SettingsApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user("01000000001", "Manager", role="manager")
        self.normal = User.objects.create_user("01000000002", "Customer")
        self.technician = User.objects.create_user("01000000003", "Tech", role="technician")
        self.client = APIClient()

    def test_health_is_public(self):
        r = self.client.get("/api/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["database"], "ok")

    def test_settings_need_manager(self):
        self.assertIn(self.client.get("/api/settings/").status_code, (401, 403))
        for user in (self.normal, self.technician):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get("/api/settings/").status_code, 403)

    def test_staff_can_list_and_edit(self):
        self.client.force_authenticate(self.staff)
        r = self.client.get("/api/settings/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), len(DEFAULT_SETTINGS))
        self.assertEqual(get_setting("otp-code-valid-minutes"), 5)
        self.assertEqual(get_setting("otp-max-requests-per-phone-per-hour"), 5)

        r = self.client.patch("/api/settings/scheduling-buffer-minutes/", {"value": 20}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        s = Setting.objects.get(key="scheduling-buffer-minutes")
        self.assertEqual(s.value, 20)
        self.assertEqual(s.updated_by, self.staff)

    def test_api_rejects_bad_value_and_key_change(self):
        self.client.force_authenticate(self.staff)
        r = self.client.patch("/api/settings/scheduling-buffer-minutes/", {"value": "abc"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.patch("/api/settings/scheduling-buffer-minutes/", {"key": "x", "value": 5}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Setting.objects.filter(key="scheduling-buffer-minutes", value=5).exists())

    def test_cannot_create_or_delete(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post("/api/settings/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete("/api/settings/scheduling-buffer-minutes/").status_code, 405)
