from django.db import migrations


def publish(apps, schema_editor):
    from accounts.terms_v1 import terms_v1_text, terms_v2_text

    TermsVersion = apps.get_model("accounts", "TermsVersion")
    current = TermsVersion.objects.order_by("-version").first()
    # Only if the live text is still our version 1 (never overwrite a manager's own version).
    if current is not None and current.version == 1 and current.text == terms_v1_text():
        TermsVersion.objects.create(version=2, text=terms_v2_text())


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_publish_terms_v1"), ("core", "0007_seed_wait_and_damage_settings")]
    operations = [migrations.RunPython(publish, migrations.RunPython.noop)]
