from django.db import migrations


def seed(apps, schema_editor):
    from core.defaults import seed_default_settings

    seed_default_settings(apps.get_model("core", "Setting"))


class Migration(migrations.Migration):
    dependencies = [("core", "0015_seed_vat_and_demo_settings")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
