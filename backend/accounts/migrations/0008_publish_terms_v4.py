from django.db import migrations


def publish(apps, schema_editor):
    from accounts.terms_v1 import terms_v3_text, terms_v4_text

    TermsVersion = apps.get_model("accounts", "TermsVersion")
    current = TermsVersion.objects.order_by("-version").first()
    # Only if the live text is still our version 3 (never overwrite a manager's own version).
    if current is not None and current.version == 3 and current.text == terms_v3_text():
        TermsVersion.objects.create(version=4, text=terms_v4_text())


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_publish_terms_v3")]
    operations = [migrations.RunPython(publish, migrations.RunPython.noop)]
