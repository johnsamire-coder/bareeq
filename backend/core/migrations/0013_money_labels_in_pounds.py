from django.db import migrations

# The app now shows and takes money settings in pounds: drop "(بالقرش)" from their names.
LABELS = {
    "cancellation-late-fee": "رسوم الإلغاء أو التأجيل المتأخر",
    "car-not-found-fee": "رسوم «الفني وصل وملقاش العربية»",
}


def update(apps, schema_editor):
    Setting = apps.get_model("core", "Setting")
    for key, label in LABELS.items():
        Setting.objects.filter(key=key).update(label=label, description="")


class Migration(migrations.Migration):
    dependencies = [("core", "0012_seed_notification_settings")]
    operations = [migrations.RunPython(update, migrations.RunPython.noop)]
