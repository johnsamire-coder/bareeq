from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from accounts.phone import InvalidPhone, normalize_phone


class Command(BaseCommand):
    help = "Create a manager account (logs in to the app with phone + one-time code)."

    def add_arguments(self, parser):
        parser.add_argument("--phone", required=True)
        parser.add_argument("--name", required=True)

    def handle(self, phone, name, **options):
        try:
            phone = normalize_phone(phone)
        except InvalidPhone as e:
            raise CommandError(str(e))
        if User.objects.filter(phone=phone).exists():
            raise CommandError(f"{phone} is already registered.")
        User.objects.create_user(phone, full_name=name, role=User.Role.MANAGER)
        self.stdout.write(self.style.SUCCESS(f"Manager created: {name} {phone}"))
