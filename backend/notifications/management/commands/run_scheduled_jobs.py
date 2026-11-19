"""Everything that must happen on its own. Run every 5 minutes on the server."""
from django.core.management.base import BaseCommand

from notifications import reminders
from orders.booking import expire_holds
from payments.online import auto_refund_cards
from payments.wallet import expire_credits
from subscriptions import service as subscriptions


class Command(BaseCommand):
    help = "Expire holds and wallet credits, and send timed reminders (safe to run often)."

    def handle(self, *args, **options):
        done = {
            "expired_holds": expire_holds(),
            "expired_wallet_credits": expire_credits(),
            "booking_reminders": reminders.booking_reminders(),
            "rating_reminders": reminders.rating_reminders(),
            "next_wash_reminders": reminders.next_wash_reminders(),
            "wallet_expiry_reminders": reminders.wallet_expiry_reminders(),
            "winback_reminders": reminders.winback_reminders(),
            "expired_subscription_months": subscriptions.expire_unpaid(),
            "subscription_renewal_reminders": subscriptions.renewal_reminders(),
            "ended_subscriptions": subscriptions.end_finished(),
            "card_refunds": auto_refund_cards(),
        }
        if options["verbosity"]:
            self.stdout.write(", ".join(f"{k}: {v}" for k, v in done.items()))
