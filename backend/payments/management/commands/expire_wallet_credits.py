from django.core.management.base import BaseCommand

from payments.wallet import expire_credits


class Command(BaseCommand):
    help = "Write 'expiry' rows for wallet credits whose date passed (run once a day)."

    def handle(self, *args, **options):
        n = expire_credits()
        if options["verbosity"]:
            self.stdout.write(f"Expired credits: {n}")
