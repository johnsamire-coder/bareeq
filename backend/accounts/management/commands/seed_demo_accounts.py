"""Three ready accounts to try the app (test server only, never the live one):
a manager, a customer with a car, an address and a booked order, and the demo
technician who gets that order. Login is by phone + the code shown on screen
(test mode). Safe to run again: nothing is made twice."""
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import TermsAcceptance, TermsVersion, User

MANAGER = ("01000000001", "مدير تجريبي")
CUSTOMER = ("01000000002", "عميل تجريبي")
TECHNICIAN = "01000000101"  # «فني تجريبي 1 - مدينة نصر» from seed_demo_technicians
NASR_CITY = (30.0729, 31.3456)


class Command(BaseCommand):
    help = "Demo manager, customer (with car, address and an order) and technician."

    def handle(self, *args, **options):
        from cars.models import CarColor, CarModel, CustomerCar
        from orders.booking import available_slots, create_order
        from orders.models import Order
        from payments.payments import confirm_with_payment
        from places.models import Address, Zone
        from services.models import Service

        import io

        call_command("seed_demo_technicians", stdout=io.StringIO())
        tech = User.objects.get(phone="+2" + TECHNICIAN)

        manager = User.objects.filter(phone="+2" + MANAGER[0]).first() or User.objects.create_user(
            MANAGER[0], MANAGER[1], role=User.Role.MANAGER)

        customer = User.objects.filter(phone="+2" + CUSTOMER[0]).first()
        if customer is None:
            customer = User.objects.create_user(CUSTOMER[0], CUSTOMER[1])
        terms = TermsVersion.current()
        if terms and not customer.terms_acceptances.filter(terms_version=terms).exists():
            TermsAcceptance.objects.create(user=customer, terms_version=terms)
        car = CustomerCar.objects.filter(customer=customer, is_active=True).first()
        if car is None:
            m = CarModel.objects.get(brand__name_en="Toyota", name="Corolla")
            car = CustomerCar.objects.create(customer=customer, brand=m.brand, model=m, year=2022,
                                             color=CarColor.objects.first(), parking="closed_garage")
        address = Address.objects.filter(customer=customer, is_active=True).first()
        if address is None:
            address = Address.objects.create(customer=customer, label="البيت", lat=NASR_CITY[0], lng=NASR_CITY[1],
                                             building="5", street="شارع عباس العقاد",
                                             zone=Zone.objects.get(name="مدينة نصر"))

        booked = "موجود قبل كده"
        if not Order.blocking().filter(customer=customer, scheduled_start__gt=timezone.now()).exists():
            items = [{"car": car.id, "services": list(Service.objects.filter(
                code__in=["exterior-wash", "interior-wash"]).values_list("id", flat=True))}]
            tomorrow = (timezone.now() + timedelta(days=1)).date().isoformat()
            from datetime import date

            from scheduling.availability import shift_for

            works = lambda d: shift_for(tech.technician_profile, date.fromisoformat(d)) is not None  # noqa: E731
            slots = [s["start"] for d in available_slots(customer, address.id, items)["days"]
                     if d["date"] >= tomorrow and works(d["date"]) for s in d["slots"]]
            booked = "مفيش مواعيد فاضية"
            for start in slots:
                try:
                    order = create_order(customer, address.id, items, start, prefer_technician=tech)
                except Exception:
                    continue
                if order.technician_id != tech.id:
                    # Another technician got it: let this hold go and try the next time.
                    order.status = Order.Status.EXPIRED
                    order.save(update_fields=["status"])
                    continue
                confirm_with_payment(order, "cash")
                booked = f"طلب {order.id} مع {order.technician.full_name}"
                break

        rows = [("المدير", manager.phone), ("العميل", customer.phone), ("الفني", tech.phone)]
        for role, phone in rows:
            self.stdout.write(f"{role}: 0{phone[3:]}")
        self.stdout.write(f"طلب تجريبي للعميل: {booked}")
