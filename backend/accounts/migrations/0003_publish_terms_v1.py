from django.db import migrations


def publish(apps, schema_editor):
    from accounts.terms_v1 import terms_v1_text

    TermsVersion = apps.get_model("accounts", "TermsVersion")
    if not TermsVersion.objects.exists():
        TermsVersion.objects.create(version=1, text=terms_v1_text())


class Migration(migrations.Migration):
    # After the cancellation settings exist, so the text matches them from the start.
    dependencies = [("accounts", "0002_seed_heard_about_options"), ("core", "0006_seed_cancellation_settings")]
    operations = [migrations.RunPython(publish, migrations.RunPython.noop)]
