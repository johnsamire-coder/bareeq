from django.apps import AppConfig


class LoyaltyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "loyalty"
    verbose_name = "الولاء والمكافآت"

    def ready(self):
        from . import discounts  # noqa: F401  (registers the wash card and referral discounts)
