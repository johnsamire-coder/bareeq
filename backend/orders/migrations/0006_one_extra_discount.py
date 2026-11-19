"""The coupon discount becomes the one "extra discount" of the order (coupon,
wash card or referral). Existing coupon discounts are kept and marked coupon."""
from django.db import migrations, models


def mark_coupons(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.filter(extra_discount__gt=0).update(extra_discount_kind="coupon")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_order_coupon_discount"),
    ]

    operations = [
        migrations.RenameField(model_name="order", old_name="coupon_discount", new_name="extra_discount"),
        migrations.AlterField(
            model_name="order",
            name="extra_discount",
            field=models.PositiveIntegerField(default=0, verbose_name="الخصم الإضافي (قرش)"),
        ),
        migrations.AddField(
            model_name="order",
            name="extra_discount_kind",
            field=models.CharField(
                blank=True,
                choices=[("coupon", "كوبون"), ("wash_card", "كارت الغسيل"), ("referral", "خصم أول طلب (دعوة)")],
                max_length=20,
                verbose_name="نوع الخصم الإضافي",
            ),
        ),
        migrations.RunPython(mark_coupons, migrations.RunPython.noop),
    ]
