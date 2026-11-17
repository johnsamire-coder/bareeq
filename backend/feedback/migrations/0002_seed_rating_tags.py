from django.db import migrations

TAGS = ["في الميعاد", "جودة الشغل", "الأخلاق", "النضافة حوالين العربية"]


def seed(apps, schema_editor):
    Tag = apps.get_model("feedback", "RatingTag")
    if not Tag.objects.exists():
        for i, name in enumerate(TAGS):
            Tag.objects.create(name=name, sort_order=i)


class Migration(migrations.Migration):
    dependencies = [("feedback", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
