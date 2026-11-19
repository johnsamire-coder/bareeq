"""Phase 2 (SPEC 11, numbers agreed with John 19 Nov 2026): cashback, invite a
friend, wash card, cancelled InstaPay money into the wallet with a bonus, and
the «we miss you» reminder."""
from datetime import timedelta

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import TermsVersion, User
from accounts.services import request_otp, verify_otp
from cars.models import CarColor, CarModel, CustomerCar
from core.errors import BusinessError
from core.models import Setting
from loyalty import referral as ref
from loyalty.models import Referral
from loyalty.wash_card import progress
from notifications.models import Notification
from notifications.reminders import winback_reminders
from orders.lifecycle import cancel_by_customer, complete_job
from orders.tests.helpers import CITY_STARS, WED, cairo, frozen_now, make_customer, make_technician
from payments import wallet
from payments.models import Payment, WalletEntry
from payments.payments import confirm_with_payment, review_instapay
from payments.tests.helpers import MEDIA, book, proof, work_until_done_photos
from places.models import Address, Zone

FAR = (30.0600, 31.3300)  # also Nasr City, but another street


def setting(key, value):
    Setting.objects.filter(key=key).update(value=value)


class Base(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()

    def day(self, i):
        return WED + timedelta(days=i)

    def order(self, customer=None, car=None, address=None, i=0, hour=10, **confirm):
        customer, car, address = customer or self.customer, car or self.car, address or self.address
        start = cairo(self.day(i), hour)
        o = book(customer, car, address, start)
        with frozen_now(start - timedelta(days=1)):
            confirm_with_payment(o, confirm.pop("method", "cash"), **confirm)
        o.refresh_from_db()
        return o

    def finish(self, o, cash=None):
        end = work_until_done_photos(o, self.tech, o.scheduled_start)
        with frozen_now(end):
            o.refresh_from_db()
            complete_job(o, self.tech, cash_collected=o.amount_to_collect if cash is None else cash)
        o.refresh_from_db()
        return o

    def entries(self, customer, kind):
        return list(WalletEntry.objects.filter(customer=customer, kind=kind).values_list("amount", flat=True))


@override_settings(MEDIA_ROOT=MEDIA)
class CashbackTests(Base):
    def test_off_by_default(self):
        self.finish(self.order())
        self.assertEqual(self.entries(self.customer, "cashback"), [])

    def test_percent_of_real_money_whole_pounds(self):
        setting("cashback-enabled", True)
        o = self.finish(self.order())  # 243 EGP cash
        self.assertEqual(self.entries(self.customer, "cashback"), [1200])  # 5% = 12.15 -> 12
        n = Notification.objects.filter(user=self.customer, kind="wallet_credit").last()
        self.assertEqual(n.title, "نزلك كاش باك")
        # once only
        from loyalty.rewards import on_completed

        on_completed(o)
        self.assertEqual(len(self.entries(self.customer, "cashback")), 1)

    def test_not_on_the_wallet_part(self):
        setting("cashback-enabled", True)
        wallet.credit(self.customer, 5000, "manual", created_by=self.manager, note="هدية")
        self.finish(self.order(wallet_amount=5000))  # 50 wallet + 193 cash
        self.assertEqual(self.entries(self.customer, "cashback"), [900])  # 5% of 193 = 9.65 -> 9

    def test_only_when_fully_paid(self):
        setting("cashback-enabled", True)
        self.finish(self.order(), cash=20000)  # technician collected less
        self.assertEqual(self.entries(self.customer, "cashback"), [])

    def test_instapay_waits_for_the_manager(self):
        setting("cashback-enabled", True)
        o = self.finish(self.order(method="instapay", proof_file=proof()))
        self.assertEqual(self.entries(self.customer, "cashback"), [])
        review_instapay(o.payments.get(), self.manager, approve=True)
        self.assertEqual(self.entries(self.customer, "cashback"), [1200])

    def test_checkout_shows_the_percent(self):
        o = book(self.customer, self.car, self.address, cairo(WED, 10))
        api = APIClient()
        api.force_authenticate(self.customer)
        self.assertEqual(api.get(f"/api/orders/{o.id}/").json()["cashback_percent"], 0)
        setting("cashback-enabled", True)
        self.assertEqual(api.get(f"/api/orders/{o.id}/").json()["cashback_percent"], 5)


@override_settings(MEDIA_ROOT=MEDIA)
class ReferralTests(Base):
    def setUp(self):
        super().setUp()
        self.friend_code = ref.code_for(self.customer)  # the existing customer invites

    def signup(self, phone="01055500001", code=None, device="dev-new"):
        code = code if code is not None else self.friend_code
        with frozen_now(cairo(WED, 8) - timedelta(days=2)):
            otp = request_otp(phone, device_id=device)
            user, is_new = verify_otp(phone, otp, signup={
                "full_name": "صاحب جديد", "terms_version": TermsVersion.current().version, "referral_code": code})
        m = CarModel.objects.get(brand__name_en="Toyota", name="Corolla")
        car = CustomerCar.objects.create(customer=user, brand=m.brand, model=m, year=2021, plate_number="ق ر ن 123",
                                         color=CarColor.objects.first(), parking="closed_garage")
        address = Address.objects.create(customer=user, label="البيت", lat=FAR[0], lng=FAR[1], building="9",
                                         zone=Zone.objects.get(name="مدينة نصر"))
        return user, car, address

    def test_code_is_fixed_and_unique(self):
        self.assertEqual(ref.code_for(self.customer), self.friend_code)
        self.assertEqual(len(self.friend_code), 7)
        other, _, _ = make_customer("01012300000")
        self.assertNotEqual(ref.code_for(other), self.friend_code)

    def test_wrong_code_at_signup_is_refused(self):
        with frozen_now(cairo(WED, 8)):
            otp = request_otp("01055500002")
            with self.assertRaises(Exception) as e:
                verify_otp("01055500002", otp, signup={"full_name": "x", "terms_version": TermsVersion.current().version,
                                                        "referral_code": "NOPE"})
        self.assertEqual(e.exception.code, "referral_code_invalid")
        self.assertFalse(User.objects.filter(phone="+201055500002").exists())

    def test_first_order_discount_then_friend_credit(self):
        user, car, address = self.signup()
        r = Referral.objects.get()
        self.assertEqual((r.referrer, r.status), (self.customer, "pending"))
        first = self.order(user, car, address)
        self.assertEqual((first.extra_discount_kind, first.extra_discount, first.amount_due), ("referral", 5000, 19300))
        second = book(user, car, address, cairo(self.day(1), 10))  # only the first order
        self.assertEqual(second.extra_discount_kind, "")
        self.finish(first)
        r.refresh_from_db()
        self.assertEqual(r.status, "credited")
        self.assertEqual(self.entries(self.customer, "referral"), [5000])
        n = Notification.objects.filter(user=self.customer, kind="wallet_credit").last()
        self.assertEqual(n.title, "صاحبك جرّب بريق")

    def test_no_credit_until_paid(self):
        user, car, address = self.signup()
        self.finish(self.order(user, car, address), cash=10000)  # not fully collected
        self.assertEqual(Referral.objects.get().status, "pending")
        self.assertEqual(self.entries(self.customer, "referral"), [])

    def test_same_address_same_plate_same_phone(self):
        user, car, address = self.signup()
        address.lat, address.lng = CITY_STARS  # the friend's address
        address.save()
        self.finish(self.order(user, car, address))
        r = Referral.objects.get()
        self.assertEqual((r.status, r.reason), ("rejected", "نفس العنوان بتاع صاحب الكود"))

    def test_same_plate(self):
        self.car.plate_number = "قرن-123"
        self.car.save()
        user, car, address = self.signup()
        self.finish(self.order(user, car, address))
        self.assertEqual(Referral.objects.get().reason, "نفس رقم العربية بتاعة صاحب الكود")

    def test_same_phone_device(self):
        with frozen_now(cairo(WED, 8) - timedelta(days=3)):
            request_otp(self.customer.phone, device_id="shared-phone")
        user, car, address = self.signup(device="shared-phone")
        self.finish(self.order(user, car, address))
        self.assertEqual(Referral.objects.get().reason, "نفس الموبايل اللي صاحب الكود بيدخل منه")

    def test_monthly_cap_goes_to_the_manager(self):
        setting("referral-monthly-cap", 0)
        user, car, address = self.signup()
        self.finish(self.order(user, car, address))
        r = Referral.objects.get()
        self.assertEqual(r.status, "review")
        self.assertTrue(Notification.objects.filter(user=self.manager, kind="referral_to_review").exists())
        api = APIClient()
        api.force_authenticate(self.manager)
        self.assertEqual(api.get("/api/manage/inbox/").json()["referrals_to_review"], 1)
        rows = api.get("/api/manage/referrals/", {"status": "review"}).json()
        self.assertEqual(rows[0]["referrer_name"], "عميل")
        self.assertEqual(api.post(f"/api/manage/referrals/{r.id}/reject/", {}, format="json").json()["code"],
                         "reason_required")
        self.assertEqual(api.post(f"/api/manage/referrals/{r.id}/approve/").json()["status"], "credited")
        self.assertEqual(self.entries(self.customer, "referral"), [5000])

    def test_bigger_coupon_replaces_the_referral_discount(self):
        from coupons.models import Coupon
        from coupons.service import apply_coupon

        user, car, address = self.signup()
        o = book(user, car, address, cairo(WED, 10))
        self.assertEqual(o.extra_discount_kind, "referral")
        Coupon.objects.create(code="BIG", kind="amount", value=8000, expires_at=cairo(WED, 23),
                              max_uses_total=10, max_uses_per_customer=1)
        with frozen_now(cairo(WED, 8)):
            o = apply_coupon(o, user, "BIG")
        self.assertEqual((o.extra_discount_kind, o.extra_discount), ("coupon", 8000))


@override_settings(MEDIA_ROOT=MEDIA)
class WashCardTests(Base):
    def setUp(self):
        super().setUp()
        setting("wash-card-every-n", 2)

    def test_every_n_orders_next_one_half_price(self):
        self.finish(self.order(i=0))
        self.assertEqual(Notification.objects.filter(user=self.customer, title="فاضلك طلب واحد").count(), 1)
        self.finish(self.order(i=1))
        self.assertTrue(Notification.objects.filter(user=self.customer, kind="wash_card",
                                                    title="طلبك الجاي عليه خصم 50%").exists())
        third = self.order(i=2)
        # 50% of 243 = 121.50 -> discount 121, pays 122
        self.assertEqual((third.extra_discount_kind, third.extra_discount, third.amount_due), ("wash_card", 12100, 12200))
        self.finish(third)
        self.assertEqual(progress(self.customer), 0)  # the card starts again
        fourth = book(self.customer, self.car, self.address, cairo(self.day(3), 10))
        self.assertEqual(fourth.extra_discount_kind, "")

    def test_only_one_booked_order_gets_it(self):
        self.finish(self.order(i=0))
        self.finish(self.order(i=1))
        a = self.order(i=2)
        b = book(self.customer, self.car, self.address, cairo(self.day(3), 10))
        self.assertEqual((a.extra_discount_kind, b.extra_discount_kind), ("wash_card", ""))

    def test_switched_off(self):
        setting("wash-card-enabled", False)
        self.finish(self.order(i=0))
        self.finish(self.order(i=1))
        self.assertEqual(self.order(i=2).extra_discount_kind, "")

    def test_customer_screen(self):
        self.finish(self.order(i=0))
        api = APIClient()
        api.force_authenticate(self.customer)
        r = api.get("/api/my-rewards/").json()
        self.assertEqual(r["wash_card"], {"enabled": True, "every_n": 2, "reward_percent": 50, "done": 1,
                                          "next_is_reward": False})
        self.assertEqual(r["referral"]["code"], self.customer.referral_code or User.objects.get(
            pk=self.customer.pk).referral_code)
        self.assertEqual((r["referral"]["new_customer_discount"], r["referral"]["referrer_credit"]), (5000, 5000))


@override_settings(MEDIA_ROOT=MEDIA)
class RefundToWalletTests(Base):
    def test_cancelled_instapay_money_into_wallet_with_bonus(self):
        o = self.order(method="instapay", proof_file=proof())
        review_instapay(o.payments.get(), self.manager, approve=True)
        with frozen_now(o.scheduled_start - timedelta(days=1)):
            cancel_by_customer(o)
        api = APIClient()
        api.force_authenticate(self.customer)
        opt = api.get(f"/api/orders/{o.id}/").json()["refund_option"]
        self.assertEqual(opt, {"amount": 24300, "bonus": 2400, "wallet_amount": 26700})  # +10%, whole pounds
        r = api.post(f"/api/orders/{o.id}/refund-to-wallet/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["wallet_balance"], 26700)
        self.assertEqual(o.payments.get().status, "refunded_to_wallet")
        self.assertEqual(api.post(f"/api/orders/{o.id}/refund-to-wallet/").json()["code"], "nothing_to_refund")
        # gone from the manager's refunds list
        self.assertFalse(Payment.objects.filter(status="refund_due").exists())

    def test_transfer_not_yet_confirmed_cannot_go_to_wallet(self):
        o = self.order(method="instapay", proof_file=proof())
        with frozen_now(o.scheduled_start - timedelta(days=1)):
            cancel_by_customer(o)
        api = APIClient()
        api.force_authenticate(self.customer)
        self.assertIsNone(api.get(f"/api/orders/{o.id}/").json()["refund_option"])

    def test_someone_else_cannot(self):
        o = self.order(method="instapay", proof_file=proof())
        other, _, _ = make_customer("01012300000")
        api = APIClient()
        api.force_authenticate(other)
        self.assertEqual(api.post(f"/api/orders/{o.id}/refund-to-wallet/").status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA)
class WinbackAndReportTests(Base):
    def test_we_miss_you_once(self):
        o = self.finish(self.order())
        with frozen_now(o.actual_end + timedelta(days=29)):
            self.assertEqual(winback_reminders(), 0)
        with frozen_now(o.actual_end + timedelta(days=31)):
            winback_reminders()
            winback_reminders()
        self.assertEqual(Notification.objects.filter(user=self.customer, kind="winback").count(), 1)

    def test_not_when_already_booked(self):
        o = self.finish(self.order())
        later = o.actual_end + timedelta(days=31)
        start = cairo(later.date() + timedelta(days=2), 10)
        b = book(self.customer, self.car, self.address, start)
        with frozen_now(start - timedelta(days=1)):
            confirm_with_payment(b, "cash")
        with frozen_now(later):
            self.assertEqual(winback_reminders(), 0)

    def test_wallet_report(self):
        setting("cashback-enabled", True)
        with frozen_now(cairo(WED, 8)):
            wallet.credit(self.customer, 5000, "manual", created_by=self.manager, note="هدية")
        o = self.order(wallet_amount=5000)
        self.finish(o)
        api = APIClient()
        api.force_authenticate(self.manager)
        r = api.get("/api/manage/reports/wallet/", {"month": "2026-11"}).json()
        credited = {c["kind"]: c["amount"] for c in r["credited"]}
        self.assertEqual((credited["manual"], credited["cashback"], r["spent"], r["expired"]), (5000, 900, 5000, 0))
        self.assertEqual(r["credited_total"], 5900)
        self.assertEqual(api.get("/api/manage/reports/wallet/", {"month": "bad"}).json()["code"], "bad_month")
        api.force_authenticate(self.customer)
        self.assertEqual(api.get("/api/manage/reports/wallet/").status_code, 403)
