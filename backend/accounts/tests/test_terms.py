from pathlib import Path

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import TermsVersion, User
from accounts.services import terms_outdated_settings
from accounts.terms_v1 import latest_terms_text, terms_v1_text, terms_v2_text, terms_v3_text, terms_v4_text, terms_v5_text
from core.models import Setting
from core.services import get_setting

DOCS_COPY = Path(__file__).resolve().parents[3] / "docs" / "TERMS-ar.md"


class TermsV1Tests(TestCase):
    def test_versions_1_2_3_published_by_migrations(self):
        self.assertEqual(TermsVersion.objects.get(version=1).text, terms_v1_text())
        self.assertEqual(TermsVersion.objects.get(version=2).text, terms_v2_text())
        self.assertEqual(TermsVersion.objects.get(version=3).text, terms_v3_text())
        self.assertEqual(TermsVersion.objects.get(version=4).text, terms_v4_text())
        self.assertEqual(TermsVersion.current().version, 5)
        self.assertEqual(TermsVersion.current().text, terms_v5_text())

    def test_docs_copy_is_identical(self):
        if not DOCS_COPY.exists():
            self.skipTest("docs folder not deployed here")
        self.assertEqual(DOCS_COPY.read_text(encoding="utf-8"), latest_terms_text())

    def test_terms_numbers_are_marked_on_a_fresh_database(self):
        marked = set(Setting.objects.filter(mentioned_in_terms=True).values_list("key", flat=True))
        self.assertEqual(marked, {"cancellation-free-until-hours", "cancellation-late-fee", "car-not-found-fee",
                                  "car-not-found-wait-minutes", "damage-report-within-hours"})

    def test_required_sections_present(self):
        text = latest_terms_text()
        for heading in ("الخدمة بتتعمل إزاي", "المواعيد", "الإلغاء والتأجيل", "ملقاش العربية", "الدفع",
                        "صور قبل وبعد", "الخدوش", "بياناتك", "الخصومات والمكافآت", "خصم واحد بس",
                        "ادعي صاحبك", "كارت الغسيل", "الاشتراك الشهري", "الطلب السريع",
                        "رسوم المسافة", "تتبع الفني"):
            self.assertIn(heading, text)

    def test_numbers_in_text_match_settings(self):
        text = latest_terms_text()
        self.assertIn(f"**{get_setting('car-not-found-wait-minutes')} دقيقة**", text)
        self.assertIn(f"**{get_setting('damage-report-within-hours')} ساعة**", text)
        hours = get_setting("cancellation-free-until-hours")
        self.assertEqual(hours, 2)
        self.assertIn("**ساعتين** قبل الميعاد", text)
        for key in ("cancellation-late-fee", "car-not-found-fee"):
            self.assertIn(f"**{get_setting(key) // 100} جنيه**", text)


class TermsOutdatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.client.force_authenticate(self.manager)

    def status(self):
        return self.client.get("/api/terms/status/").json()

    def test_fresh_install_is_up_to_date(self):
        self.assertEqual(terms_outdated_settings(), [])
        self.assertEqual(self.status(), {"current_version": 5, "needs_new_version": False, "changed_settings": []})

    def test_changing_a_terms_number_asks_for_new_version(self):
        r = self.client.patch("/api/settings/cancellation-late-fee/", {"value": 7500}, format="json")
        self.assertEqual(r.status_code, 200)
        st = self.status()
        self.assertTrue(st["needs_new_version"])
        self.assertEqual(st["changed_settings"][0]["key"], "cancellation-late-fee")

        TermsVersion.objects.create(text="نسخة 2 فيها 75 جنيه")
        self.assertFalse(self.status()["needs_new_version"])

    def test_saving_same_value_or_other_settings_does_not_warn(self):
        self.client.patch("/api/settings/cancellation-late-fee/", {"value": 5000}, format="json")
        self.client.patch("/api/settings/scheduling-buffer-minutes/", {"value": 20}, format="json")
        self.assertFalse(self.status()["needs_new_version"])

    def test_status_is_manager_only(self):
        self.client.force_authenticate(User.objects.create_user("01012345678", "c"))
        self.assertEqual(self.client.get("/api/terms/status/").status_code, 403)

    def test_admin_shows_reminder(self):
        admin_user = User.objects.create_superuser("01000000009", "Admin", password="pw-For-Test-1")
        self.client.force_login(admin_user)
        s = Setting.objects.get(key="cancellation-free-until-hours")
        s.value = 3
        s.save()
        for url in ("/admin/core/setting/", "/admin/accounts/termsversion/"):
            r = self.client.get(url)
            self.assertContains(r, "انشر نسخة شروط جديدة", msg_prefix=url)
        r = self.client.get("/admin/accounts/termsversion/add/")
        self.assertContains(r, "شروط وأحكام استخدام")  # new version starts from current text
