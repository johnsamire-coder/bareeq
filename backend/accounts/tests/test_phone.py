from django.test import SimpleTestCase

from accounts.phone import InvalidPhone, normalize_phone


class PhoneTests(SimpleTestCase):
    def test_accepted_forms(self):
        for raw in ("01012345678", "+201012345678", "00201012345678", "201012345678",
                    "1012345678", "010 1234 5678", "010-1234-5678", "٠١٠١٢٣٤٥٦٧٨"):
            self.assertEqual(normalize_phone(raw), "+201012345678", raw)

    def test_all_egyptian_networks(self):
        for prefix in ("010", "011", "012", "015"):
            self.assertEqual(normalize_phone(prefix + "12345678"), "+20" + prefix[1:] + "12345678")

    def test_rejected(self):
        for raw in ("", "0101234567", "010123456789", "01312345678", "0223456789", "abc", None, "+966501234567"):
            with self.assertRaises(InvalidPhone, msg=raw):
                normalize_phone(raw)
