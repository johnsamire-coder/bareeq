import re
from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import HeardAboutOption, OtpRequest, TermsAcceptance, TermsVersion, User
from accounts.otp_senders import OtpSender
from core.models import Setting

SENT = []


class FakeSender(OtpSender):
    def send(self, phone, code):
        SENT.append((phone, code))


@override_settings(OTP_SENDER="accounts.tests.test_login.FakeSender")
class LoginApiTests(TestCase):
    PHONE = "01012345678"

    def setUp(self):
        SENT.clear()
        self.client = APIClient()
        self.terms = TermsVersion.objects.create(text="الشروط نسخة 1")

    # helpers
    def request_code(self, phone=PHONE, device="dev-1"):
        return self.client.post("/api/auth/otp/request/", {"phone": phone, "device_id": device}, format="json")

    def last_code(self):
        return SENT[-1][1]

    def verify(self, code, phone=PHONE, **extra):
        return self.client.post("/api/auth/otp/verify/", {"phone": phone, "code": code, **extra}, format="json")

    def signup_data(self):
        return {"full_name": "أحمد علي", "terms_version": self.terms.version, "device_type": "android"}

    # sign-up
    def test_new_customer_signup_flow(self):
        self.assertEqual(self.request_code().status_code, 200)
        code = self.last_code()
        self.assertTrue(re.fullmatch(r"\d{6}", code))
        self.assertEqual(SENT[-1][0], "+201012345678")

        # First try without name: app is told to show the sign-up fields, code not used up.
        r = self.verify(code)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "signup_required")

        heard = HeardAboutOption.objects.first()
        r = self.verify(code, **self.signup_data(), referral_code="ABC123", heard_about=heard.id)
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertTrue(body["is_new"])
        self.assertEqual(body["user"]["role"], "customer")
        self.assertFalse(body["user"]["needs_terms_acceptance"])

        user = User.objects.get(phone="+201012345678")
        self.assertEqual(user.full_name, "أحمد علي")
        self.assertEqual(user.signup_device_type, "android")
        self.assertEqual(user.referral_code_entered, "ABC123")
        self.assertEqual(user.heard_about, heard)
        self.assertFalse(user.has_usable_password())
        acc = TermsAcceptance.objects.get(user=user)
        self.assertEqual(acc.terms_version, self.terms)
        self.assertIsNotNone(acc.accepted_at)

        # Token works.
        self.client.credentials(HTTP_AUTHORIZATION="Token " + body["token"])
        self.assertEqual(self.client.get("/api/me/").json()["phone"], "+201012345678")

    def test_code_cannot_be_reused(self):
        self.request_code()
        code = self.last_code()
        self.assertEqual(self.verify(code, **self.signup_data()).status_code, 200)
        r = self.verify(code)
        self.assertEqual(r.json()["code"], "code_expired")

    def test_signup_needs_current_terms_version(self):
        self.request_code()
        code = self.last_code()
        TermsVersion.objects.create(text="نسخة 2")
        r = self.verify(code, **self.signup_data())  # still sends version 1
        self.assertEqual(r.json()["code"], "terms_outdated")
        self.assertFalse(User.objects.exists())

    def test_signup_blocked_when_no_terms_published(self):
        TermsVersion.objects.all().delete()
        self.request_code()
        r = self.verify(self.last_code(), full_name="x", terms_version=1)
        self.assertEqual(r.status_code, 503)
        self.assertFalse(User.objects.exists())

    # existing users
    def test_existing_user_logs_in_without_signup_data(self):
        User.objects.create_user(self.PHONE, "Old", role="customer")
        self.request_code(phone="+201012345678")
        r = self.verify(self.last_code())
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["is_new"])
        self.assertEqual(User.objects.count(), 1)

    def test_technician_added_by_manager_logs_in_as_technician(self):
        manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.client.force_authenticate(manager)
        r = self.client.post("/api/technicians/", {"phone": "01122223333", "full_name": "محمد الفني"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.client.force_authenticate(None)

        self.request_code(phone="01122223333")
        r = self.verify(self.last_code(), phone="01122223333")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user"]["role"], "technician")
        # Technicians are not asked to accept customer terms.
        self.assertFalse(r.json()["user"]["needs_terms_acceptance"])

    def test_disabled_user_cannot_log_in(self):
        User.objects.create_user(self.PHONE, "Old", is_active=False)
        self.request_code()
        r = self.verify(self.last_code())
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["code"], "account_disabled")

    # code checks
    def test_wrong_code_counted_then_locked(self):
        User.objects.create_user(self.PHONE, "Old")
        self.request_code()
        good = self.last_code()
        bad = "000000" if good != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.verify(bad).json()["code"], "wrong_code")
        self.assertEqual(OtpRequest.objects.get().wrong_attempts, 5)
        # Even the right code is refused now.
        self.assertEqual(self.verify(good).json()["code"], "too_many_attempts")

    def test_wrong_attempts_limit_is_a_setting(self):
        Setting.objects.filter(key="otp-max-wrong-attempts").update(value=2)
        User.objects.create_user(self.PHONE, "Old")
        self.request_code()
        good = self.last_code()
        bad = "000000" if good != "000000" else "111111"
        self.verify(bad)
        self.verify(bad)
        self.assertEqual(self.verify(good).json()["code"], "too_many_attempts")

    def test_code_expires_after_setting_minutes(self):
        User.objects.create_user(self.PHONE, "Old")
        self.request_code()
        otp = OtpRequest.objects.get()
        self.assertAlmostEqual((otp.expires_at - otp.created_at).total_seconds(), 5 * 60, delta=1)
        later = timezone.now() + timedelta(minutes=5, seconds=1)
        with mock.patch("django.utils.timezone.now", return_value=later):
            self.assertEqual(self.verify(self.last_code()).json()["code"], "code_expired")

    def test_only_latest_code_works(self):
        User.objects.create_user(self.PHONE, "Old")
        self.request_code()
        first = self.last_code()
        self.request_code()
        second = self.last_code()
        if first != second:
            self.assertEqual(self.verify(first).json()["code"], "wrong_code")
        self.assertEqual(self.verify(second).status_code, 200)

    def test_code_is_not_stored_in_plain_text(self):
        self.request_code()
        otp = OtpRequest.objects.get()
        self.assertNotIn(self.last_code(), otp.code_hash)
        self.assertEqual(len(otp.code_hash), 64)

    # rate limits
    def test_five_requests_per_phone_per_hour(self):
        for i in range(5):
            self.assertEqual(self.request_code(device=f"d{i}").status_code, 200)
        r = self.request_code(device="d-new")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(len(SENT), 5)
        # An hour later it works again.
        later = timezone.now() + timedelta(hours=1, minutes=1)
        with mock.patch("django.utils.timezone.now", return_value=later):
            self.assertEqual(self.request_code(device="d-new").status_code, 200)

    def test_five_requests_per_device_per_hour(self):
        for i in range(5):
            self.assertEqual(self.request_code(phone=f"0101234560{i}", device="same").status_code, 200)
        self.assertEqual(self.request_code(phone="01012345609", device="same").status_code, 429)

    def test_rate_limit_is_a_setting(self):
        Setting.objects.filter(key="otp-max-requests-per-phone-per-hour").update(value=2)
        self.request_code(device="a")
        self.request_code(device="b")
        self.assertEqual(self.request_code(device="c").status_code, 429)

    def test_invalid_phone_rejected(self):
        r = self.request_code(phone="12345")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.json())
        self.assertEqual(SENT, [])

    # logout / terms
    def test_logout_kills_token(self):
        self.request_code()
        token = self.verify(self.last_code(), **self.signup_data()).json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)
        self.assertEqual(self.client.get("/api/me/").status_code, 401)

    def test_new_terms_version_must_be_accepted(self):
        self.request_code()
        token = self.verify(self.last_code(), **self.signup_data()).json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)
        v2 = TermsVersion.objects.create(text="نسخة 2")
        self.assertTrue(self.client.get("/api/me/").json()["needs_terms_acceptance"])
        self.assertEqual(self.client.post("/api/terms/accept/", {"terms_version": 1}, format="json").status_code, 400)
        self.assertEqual(
            self.client.post("/api/terms/accept/", {"terms_version": v2.version}, format="json").status_code, 200
        )
        self.assertFalse(self.client.get("/api/me/").json()["needs_terms_acceptance"])

    def test_current_terms_public(self):
        TermsVersion.objects.create(text="نسخة 2")
        r = self.client.get("/api/terms/current/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["version"], 2)
        self.assertEqual(r.json()["text"], "نسخة 2")

    def test_heard_about_list_public(self):
        r = self.client.get("/api/heard-about-options/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0]["label"], "فيسبوك")

    def test_customer_cannot_change_own_role_or_phone(self):
        self.request_code()
        token = self.verify(self.last_code(), **self.signup_data()).json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)
        r = self.client.patch("/api/me/", {"role": "manager", "phone": "01099999999", "full_name": "أحمد"}, format="json")
        self.assertEqual(r.status_code, 200)
        u = User.objects.get()
        self.assertEqual((u.role, u.phone, u.full_name), ("customer", "+201012345678", "أحمد"))


class TermsVersionTests(TestCase):
    def test_versions_number_themselves_and_are_frozen(self):
        a = TermsVersion.objects.create(text="1")
        b = TermsVersion.objects.create(text="2")
        self.assertEqual((a.version, b.version), (1, 2))
        self.assertEqual(TermsVersion.current(), b)
        a.text = "changed"
        with self.assertRaises(ValueError):
            a.save()


class TechnicianApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer = User.objects.create_user("01000000002", "Cust")

    def test_only_manager(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/technicians/").status_code, 403)
        r = self.client.post("/api/technicians/", {"phone": "01122223333", "full_name": "x"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_duplicate_phone_and_missing_name(self):
        self.client.force_authenticate(self.manager)
        r = self.client.post("/api/technicians/", {"phone": "+201000000002", "full_name": "x"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/technicians/", {"phone": "01122223333", "full_name": "  "}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_list_and_deactivate(self):
        self.client.force_authenticate(self.manager)
        r = self.client.post("/api/technicians/", {"phone": "01122223333", "full_name": "محمد"}, format="json")
        tid = r.json()["id"]
        self.assertEqual([t["full_name"] for t in self.client.get("/api/technicians/").json()], ["محمد"])
        r = self.client.patch(f"/api/technicians/{tid}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.get(pk=tid).is_active)
        self.assertEqual(self.client.delete(f"/api/technicians/{tid}/").status_code, 405)
