"""Five DEMO technicians for testing (not for the live server).

- 2 for Nasr City, 2 for Obour + Madinaty together, 1 reserve covering all three.
- Every day 9:00 to 22:00, each with a different weekly day off; all work on Friday.
- Phone numbers 01000000101..105 are placeholders: deactivate these accounts
  and add the real technicians before launch.
"""
from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from accounts.phone import normalize_phone
from places.models import Zone
from scheduling.models import WeeklyShift

NASR, OBOUR, MADINATY = "مدينة نصر", "العبور", "مدينتي"
SAT, SUN, MON, TUE, WED = 5, 6, 0, 1, 2

# phone, name, zones, start label, (lat, lng), weekly day off
DEMO = [
    ("01000000101", "فني تجريبي 1 - مدينة نصر", [NASR], "مدينة نصر", (30.0600, 31.3400), SAT),
    ("01000000102", "فني تجريبي 2 - مدينة نصر", [NASR], "مدينة نصر", (30.0600, 31.3400), SUN),
    ("01000000103", "فني تجريبي 3 - العبور ومدينتي", [OBOUR, MADINATY], "العبور", (30.2280, 31.4800), MON),
    ("01000000104", "فني تجريبي 4 - العبور ومدينتي", [OBOUR, MADINATY], "مدينتي", (30.1020, 31.6400), TUE),
    ("01000000105", "فني تجريبي 5 - احتياطي", [NASR, OBOUR, MADINATY], "مدينة نصر", (30.0600, 31.3400), WED),
]


class Command(BaseCommand):
    help = "Create 5 demo technicians with zones, start points and working hours (testing only)."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for phone, name, zones, label, (lat, lng), day_off in DEMO:
            if User.objects.filter(phone=normalize_phone(phone)).exists():
                continue
            user = User.objects.create_user(phone, full_name=name, role=User.Role.TECHNICIAN)
            profile = user.technician_profile
            profile.zones.set(Zone.objects.filter(name__in=zones))
            profile.start_label, profile.start_lat, profile.start_lng = label, lat, lng
            profile.save()
            for weekday in range(7):
                if weekday != day_off:
                    WeeklyShift.objects.create(technician=profile, weekday=weekday, start_time=time(9),
                                               end_time=time(22))
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Demo technicians created: {created}"))
