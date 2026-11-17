"""A basic test list of materials with test unit prices, marked provisional.
Only added when the list is empty; the manager replaces them with real ones."""
from django.db import migrations

MATERIALS = [  # name, unit, unit price in pounds
    ("شامبو عربيات", "liter", 120),
    ("واكس", "box", 350),
    ("ملمع تابلوه", "liter", 180),
    ("مناديل مايكروفايبر", "piece", 40),
    ("معطر", "piece", 60),
]


def seed(apps, schema_editor):
    Material = apps.get_model("payments", "Material")
    if Material.objects.exists():
        return
    for i, (name, unit, pounds) in enumerate(MATERIALS, start=1):
        Material.objects.create(name=name, unit=unit, unit_cost=pounds * 100, sort_order=i, is_provisional=True)


class Migration(migrations.Migration):
    dependencies = [("payments", "0003_material_is_provisional")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
