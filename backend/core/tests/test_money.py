"""RULE: every amount the customer pays is whole pounds. Prices themselves are
never changed; the piastres go into the DISCOUNT:
- normally the discount is rounded DOWN (VIP 100.50 discount -> 100, total 570);
- if that would make the discount negative (no discount and a price like
  162.50), the discount is rounded UP instead (customer pays 162)."""
import random

from django.test import SimpleTestCase

from core.money import whole_pound_discount


class WholePoundDiscountTests(SimpleTestCase):
    def test_examples(self):
        self.assertEqual(whole_pound_discount(67000, 10050), 10000)  # VIP: pays 570
        self.assertEqual(whole_pound_discount(27000, 2700), 2700)    # already whole
        self.assertEqual(whole_pound_discount(16250, 0), 50)         # no discount: pays 162
        self.assertEqual(whole_pound_discount(16250, 20), 50)        # 162.30: cannot go down 0.70, so up 0.30 -> pays 162
        self.assertEqual(whole_pound_discount(16250, 300), 250)      # 3 -> 2.50, pays 140

    def test_property_many_random_amounts(self):
        rnd = random.Random(7)
        for _ in range(20000):
            gross = rnd.randint(0, 500000)
            raw = rnd.randint(0, gross)
            d = whole_pound_discount(gross, raw)
            self.assertEqual((gross - d) % 100, 0, (gross, raw, d))
            self.assertGreaterEqual(d, 0)
            self.assertLessEqual(d, gross)
            self.assertLess(abs(d - raw), 100)  # never moves more than 99 piastres
