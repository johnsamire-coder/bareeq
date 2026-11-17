from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user table. Defined from day one so step 3 (phone login and roles)
    can extend it without a painful migration."""

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمين"
