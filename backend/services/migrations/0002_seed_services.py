from django.db import migrations


def seed(apps, schema_editor):
    from services.seed_data import seed_services

    seed_services(
        apps.get_model("services", "Service"),
        apps.get_model("services", "ServicePrice"),
        apps.get_model("services", "ServiceDuration"),
        apps.get_model("services", "Bundle"),
        apps.get_model("places", "Zone"),
    )


class Migration(migrations.Migration):
    dependencies = [("services", "0001_initial"), ("places", "0002_seed_zones")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
