from django.db import migrations

OPTIONS = ["فيسبوك", "انستجرام", "تيك توك", "جوجل", "صاحب أو قريب", "شفت العربية بتاعتكم", "حاجة تانية"]


def seed(apps, schema_editor):
    Option = apps.get_model("accounts", "HeardAboutOption")
    if not Option.objects.exists():
        for i, label in enumerate(OPTIONS):
            Option.objects.create(label=label, sort_order=i)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
