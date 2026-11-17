"""Test oil types (common in Egypt) with test prices, marked provisional.
Only added when the list is empty; the manager replaces them with real ones."""
from django.db import migrations

OILS = [  # name, description, price in pounds
    ("موبيل سوبر 2000", "10W-40 نص صناعي • 4 لتر", 1300),
    ("شل هيليكس HX7", "10W-40 نص صناعي • 4 لتر", 1400),
    ("كاسترول ماجناتك", "10W-40 نص صناعي • 4 لتر", 1500),
    ("توتال كوارتز 7000", "10W-40 نص صناعي • 4 لتر", 1250),
    ("موبيل 1", "5W-30 صناعي بالكامل • 4 لتر", 2800),
]


def seed(apps, schema_editor):
    OilType = apps.get_model("services", "OilType")
    if OilType.objects.exists():
        return
    for i, (name, desc, pounds) in enumerate(OILS, start=1):
        OilType.objects.create(name=name, description=desc, price=pounds * 100, sort_order=i, is_provisional=True)


class Migration(migrations.Migration):
    dependencies = [("services", "0003_oiltype_is_provisional")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
