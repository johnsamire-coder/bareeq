"""Temporary values until the client sends the real ones: test oil types and
materials marked provisional, VAT off with an empty rate, and test mode."""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from core.models import Setting
from core.services import get_setting
from payments.models import Material
from services.models import OilType


class TestValuesTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def test_test_oils_and_materials_are_marked(self):
        self.assertEqual(OilType.objects.count(), 5)
        self.assertEqual(Material.objects.count(), 5)
        self.assertFalse(OilType.objects.filter(is_provisional=False).exists())
        self.assertFalse(Material.objects.filter(is_provisional=False).exists())
        names = set(Material.objects.values_list("name", flat=True))
        self.assertEqual(names, {"شامبو عربيات", "واكس", "ملمع تابلوه", "مناديل مايكروفايبر", "معطر"})

    def test_manager_edit_clears_the_mark(self):
        oil = OilType.objects.first()
        r = self.api.patch(f"/api/manage/oil-types/{oil.id}/", {"price": 150000}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(r.json()["is_provisional"])
        mat = Material.objects.first()
        r = self.api.patch(f"/api/manage/materials/{mat.id}/", {"unit_cost": 9000}, format="json")
        self.assertFalse(r.json()["is_provisional"])
        # The others stay "test".
        self.assertEqual(OilType.objects.filter(is_provisional=True).count(), 4)
        # The manager can't mark a price as provisional himself.
        r = self.api.patch(f"/api/manage/materials/{mat.id}/", {"is_provisional": True}, format="json")
        self.assertFalse(r.json()["is_provisional"])

    def test_vat_off_and_empty(self):
        self.assertIs(get_setting("vat-enabled"), False)
        self.assertIsNone(get_setting("vat-percent"))
        # The rate can be typed and emptied again.
        self.assertEqual(self.api.patch("/api/settings/vat-percent/", {"value": 14}, format="json").status_code, 200)
        r = self.api.patch("/api/settings/vat-percent/", {"value": None}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNone(get_setting("vat-percent"))
        # Other settings can't be emptied.
        r = self.api.patch("/api/settings/otp-code-valid-minutes/", {"value": None}, format="json")
        self.assertEqual(r.status_code, 400)
        # Invoices have no tax yet, so it can't be switched on.
        r = self.api.patch("/api/settings/vat-enabled/", {"value": True}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIs(get_setting("vat-enabled"), False)

    def test_demo_mode_shows_the_code(self):
        anon = APIClient()
        self.assertEqual(anon.get("/api/app-config/").json(), {"demo_mode": True})
        r = anon.post("/api/auth/otp/request/", {"phone": "01011112222"}, format="json").json()
        code = r["demo_code"]
        self.assertEqual(len(code), 6)
        r = anon.post("/api/auth/otp/verify/", {"phone": "01011112222", "code": code}, format="json")
        self.assertEqual(r.json()["code"], "signup_required")  # the code is right; a new number needs a name
        # Switched off: the code is not shown any more.
        Setting.objects.filter(key="demo-mode").update(value=False)
        self.assertEqual(anon.get("/api/app-config/").json(), {"demo_mode": False})
        r = anon.post("/api/auth/otp/request/", {"phone": "01011113333"}, format="json").json()
        self.assertNotIn("demo_code", r)
