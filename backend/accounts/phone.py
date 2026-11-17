"""Egyptian mobile numbers, stored in one form: +201XXXXXXXXX."""
import re

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_LOCAL = re.compile(r"^01[0125]\d{8}$")


class InvalidPhone(ValueError):
    pass


def normalize_phone(raw):
    if raw is None:
        raise InvalidPhone("رقم الموبايل مطلوب.")
    s = str(raw).translate(_ARABIC_DIGITS)
    s = re.sub(r"[\s\-()]", "", s)
    if s.startswith("+20"):
        s = "0" + s[3:]
    elif s.startswith("0020"):
        s = "0" + s[4:]
    elif s.startswith("20") and len(s) == 12:
        s = "0" + s[2:]
    elif s.startswith("1") and len(s) == 10:
        s = "0" + s
    if not _LOCAL.match(s):
        raise InvalidPhone("رقم الموبايل مش صحيح. اكتب رقم مصري زي 01012345678.")
    return "+20" + s[1:]
