from django.db import migrations


def publish(apps, schema_editor):
    from accounts.terms_v1 import terms_v2_text, terms_v3_text

    TermsVersion = apps.get_model("accounts", "TermsVersion")
    current = TermsVersion.objects.order_by("-version").first()
    # Only if the live text is still our version 2 (never overwrite a manager's own version).
    if current is not None and current.version == 2 and current.text == terms_v2_text():
        TermsVersion.objects.create(version=3, text=terms_v3_text())


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_user_referral_code")]
    operations = [migrations.RunPython(publish, migrations.RunPython.noop)]
