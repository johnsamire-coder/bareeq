"""Who gets which notification, and that timed reminders go out once only.

Push to phones is not connected yet (no Firebase project): every notification
is stored in the in-app list and marked 'push not configured'."""
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import User
from accounts.services import verify_otp
from accounts.models import TermsVersion
from cars.models import CarColor, CarModel, CustomerCar
from notifications.models import Notification
from orders.booking import reassign
from orders.lifecycle import arrived, called_customer, car_not_found, complete_job, on_the_way
from orders.tests.helpers import WED, cairo, frozen_now, make_customer, make_technician
from payments import wallet
from payments.payments import confirm_with_payment
from payments.tests.helpers import MEDIA, book, proof, work_until_done_photos
from places.models import AreaRequest, Zone

START = cairo(WED, 14)
BEFORE = START - timedelta(days=1)


def kinds(user):
    return list(Notification.objects.filter(user=user).order_by("id").values_list("kind", flat=True))


@override_settings(MEDIA_ROOT=MEDIA)
class OrderEventsTests(TestCase):
    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)

    def test_confirm_on_the_way_done(self):
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "cash")
        n = Notification.objects.get(user=self.customer, kind="booking_confirmed")
        self.assertEqual(n.data["order"], self.order.id)
        self.assertIn("18/11 الساعة 2:00 م", n.body)  # 14:00 shown as 2:00 evening
        self.assertEqual(n.push_status, "not_configured")
        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            complete_job(self.order, self.tech, cash_collected=self.order.amount_due)
        self.assertEqual(kinds(self.customer), ["booking_confirmed", "technician_on_the_way", "job_done"])
        on_way = Notification.objects.get(kind="technician_on_the_way")
        self.assertIn(self.tech.full_name, on_way.body)
        done = Notification.objects.get(kind="job_done")
        self.assertEqual(done.data, {"order": self.order.id, "action": "rate"})

    def test_instapay_waiting_alerts_managers(self):
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "instapay", proof_file=proof())
        self.assertEqual(kinds(self.manager), ["instapay_to_review"])

    def test_reassign_tells_customer_new_name(self):
        t2 = make_technician("01100000002")
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "cash")
            reassign(self.order, t2)
        n = Notification.objects.get(user=self.customer, kind="technician_changed")
        self.assertIn(t2.full_name, n.body)

    def test_car_not_found_tells_customer_and_managers(self):
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "cash")
        with frozen_now(START):
            on_the_way(self.order, self.tech)
            arrived(self.order, self.tech)
            called_customer(self.order, self.tech)
        with frozen_now(START + timedelta(minutes=16)):
            car_not_found(self.order, self.tech, 30.07, 31.34)
        self.assertIn("car_not_found", kinds(self.customer))
        self.assertEqual(kinds(self.manager), ["car_not_found"])


class AccountAndCatalogEventsTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")

    def test_welcome_after_signup(self):
        from accounts.models import OtpRequest
        from accounts.services import request_otp
        from unittest import mock

        with mock.patch("accounts.otp_senders.ConsoleOtpSender.send") as send:
            request_otp("01012345678")
            code = send.call_args[0][1]
        user, is_new = verify_otp("01012345678", code, {"full_name": "أحمد", "terms_version": TermsVersion.current().version})
        self.assertEqual(kinds(user), ["welcome"])

    def test_unlisted_model_alerts_managers(self):
        customer = User.objects.create_user("01012345678", "c")
        m = CarModel.objects.get(brand__name_en="Kia", name="Rio")
        CustomerCar.objects.create(customer=customer, brand=m.brand, unlisted_model_name="EV9", size_class="suv",
                                   year=2024, color=CarColor.objects.first(), parking="street")
        self.assertEqual(kinds(self.manager), ["car_model_to_review"])

    def test_wallet_credit_tells_customer(self):
        customer = User.objects.create_user("01012345678", "c")
        wallet.credit(customer, 5000, "manual", created_by=self.manager, note="هدية")
        self.assertEqual(kinds(customer), ["wallet_credit"])

    def test_area_now_covered(self):
        customer = User.objects.create_user("01012345678", "c")
        req = AreaRequest.objects.create(customer=customer, lat=29.96, lng=31.25, area_name="المعادي")
        Zone(name="المعادي", polygon=[[29.95, 31.24], [29.97, 31.24], [29.97, 31.27], [29.95, 31.27]]).save()
        self.assertEqual(kinds(customer), ["area_now_covered"])
        req.refresh_from_db()
        self.assertIsNotNone(req.notified_at)
        Zone.objects.get(name="المعادي").save()  # saving again does not repeat it
        self.assertEqual(kinds(customer), ["area_now_covered"])


@override_settings(MEDIA_ROOT=MEDIA)
class TimedRemindersTests(TestCase):
    """The 'run_scheduled_jobs' command runs every few minutes on the server."""

    def setUp(self):
        self.tech = make_technician("01100000001")
        self.manager = User.objects.create_user("01000000001", "Boss", role="manager")
        self.customer, self.car, self.address = make_customer()
        self.order = book(self.customer, self.car, self.address, START)
        with frozen_now(BEFORE):
            confirm_with_payment(self.order, "cash")

    def run_jobs(self, when):
        with frozen_now(when):
            call_command("run_scheduled_jobs", verbosity=0)

    def test_one_hour_reminder_once(self):
        self.run_jobs(START - timedelta(minutes=61))
        self.assertNotIn("booking_reminder", kinds(self.customer))
        self.run_jobs(START - timedelta(minutes=59))
        self.run_jobs(START - timedelta(minutes=30))
        self.assertEqual(kinds(self.customer).count("booking_reminder"), 1)

    def test_rating_reminder_after_24h_once_and_not_if_rated(self):
        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            complete_job(self.order, self.tech, cash_collected=self.order.amount_due)
        self.run_jobs(end + timedelta(hours=23))
        self.assertNotIn("rating_reminder", kinds(self.customer))
        self.run_jobs(end + timedelta(hours=25))
        self.run_jobs(end + timedelta(hours=30))
        self.assertEqual(kinds(self.customer).count("rating_reminder"), 1)

    def test_next_wash_after_14_days(self):
        end = work_until_done_photos(self.order, self.tech, START)
        with frozen_now(end):
            complete_job(self.order, self.tech, cash_collected=self.order.amount_due)
        self.run_jobs(end + timedelta(days=13))
        self.assertNotIn("next_wash", kinds(self.customer))
        self.run_jobs(end + timedelta(days=14, minutes=1))
        self.run_jobs(end + timedelta(days=15))
        self.assertEqual(kinds(self.customer).count("next_wash"), 1)

    def test_wallet_expiry_reminder_7_days_before(self):
        with frozen_now(BEFORE):
            c = wallet.credit(self.customer, 5000, "manual", created_by=self.manager, note="x")
        self.run_jobs(c.expires_at - timedelta(days=8))
        self.assertNotIn("wallet_expiring", kinds(self.customer))
        self.run_jobs(c.expires_at - timedelta(days=6))
        self.run_jobs(c.expires_at - timedelta(days=5))
        self.assertEqual(kinds(self.customer).count("wallet_expiring"), 1)
