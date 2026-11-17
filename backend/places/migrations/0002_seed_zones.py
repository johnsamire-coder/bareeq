from django.db import migrations

# ROUGH shapes only, for testing. The manager redraws them on the map in the
# dashboard. Points are [lat, lng].
ZONES = [
    ("مدينة نصر", [
        [30.0935, 31.3050], [30.0990, 31.3330], [30.0830, 31.3700], [30.0600, 31.4000],
        [30.0330, 31.3800], [30.0320, 31.3400], [30.0480, 31.3120], [30.0700, 31.3000],
    ]),
    ("العبور", [[30.2600, 31.4400], [30.2600, 31.5200], [30.1850, 31.5200], [30.1850, 31.4400]]),
    ("مدينتي", [[30.1300, 31.6050], [30.1300, 31.6800], [30.0700, 31.6800], [30.0700, 31.6050]]),
]


def seed(apps, schema_editor):
    Zone = apps.get_model("places", "Zone")
    if not Zone.objects.exists():
        for i, (name, polygon) in enumerate(ZONES):
            Zone.objects.create(name=name, polygon=polygon, sort_order=i)


class Migration(migrations.Migration):
    dependencies = [("places", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
