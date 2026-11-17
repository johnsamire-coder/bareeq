from .models import Setting


class SettingMissing(KeyError):
    pass


def get_setting(key):
    """Return the current value of a business setting.

    Raises SettingMissing instead of silently falling back to a hard-coded
    number, so a forgotten setting is noticed immediately.
    """
    try:
        return Setting.objects.values_list("value", flat=True).get(key=key)
    except Setting.DoesNotExist:
        raise SettingMissing(f"Setting '{key}' is not in the database") from None
