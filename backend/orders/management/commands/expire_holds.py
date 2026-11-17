from django.core.management.base import BaseCommand

from orders.booking import expire_holds


class Command(BaseCommand):
    help = "Mark unpaid temporary holds whose time ran out as expired (run every few minutes)."

    def handle(self, *args, **options):
        n = expire_holds()
        if options["verbosity"]:
            self.stdout.write(f"Expired holds: {n}")
