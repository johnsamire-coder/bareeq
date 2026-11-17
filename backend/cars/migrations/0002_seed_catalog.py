from django.db import migrations


def seed(apps, schema_editor):
    from cars.catalog_seed import seed_catalog

    seed_catalog(apps.get_model("cars", "CarBrand"), apps.get_model("cars", "CarModel"), apps.get_model("cars", "CarColor"))


class Migration(migrations.Migration):
    dependencies = [("cars", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
