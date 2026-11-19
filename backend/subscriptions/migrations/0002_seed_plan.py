"""The starting plan agreed with John (19 Nov 2026): 4 washes a month,
exterior + interior, 15% off the normal price. The manager edits it."""
from django.db import migrations


def seed(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "SubscriptionPlan")
    Service = apps.get_model("services", "Service")
    if Plan.objects.exists():
        return
    services = list(Service.objects.filter(code__in=["exterior-wash", "interior-wash"]))
    if len(services) != 2:
        return
    plan = Plan.objects.create(name="اشتراك شهري: غسيل برا وجوا", washes_per_month=4, discount_percent=15,
                               sort_order=1)
    plan.services.set(services)


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial"), ("services", "0004_seed_test_oil_types")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
