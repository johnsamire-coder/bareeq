"""Price calculation. Expected numbers worked out by hand from the demo rules
(Nasr City sedan: exterior 150, interior 120, engine 200, ext. detailing 800,
int. detailing 900, polish 1500, headlights 200, oil change 250 pounds)."""
from django.test import SimpleTestCase, TestCase

from core.errors import BusinessError
from core.models import Setting
from places.models import Zone
from services.models import Bundle, OilType, Service, ServicePrice
from services.pricing import build_quote, percent_of
from services.seed_data import provisional_price_pounds


def ids(*codes):
    by = dict(Service.objects.values_list("code", "id"))
    return [by[c] for c in codes]


class PercentTests(SimpleTestCase):
    def test_rounding_half_up_in_piastres(self):
        self.assertEqual(percent_of(27000, 10), 2700)
        self.assertEqual(percent_of(67000, 15), 10050)
        self.assertEqual(percent_of(333, 15), 50)   # 49.95 -> 50
        self.assertEqual(percent_of(330, 15), 50)   # 49.5 -> 50
        self.assertEqual(percent_of(329, 15), 49)   # 49.35 -> 49


class SeedPriceRuleTests(SimpleTestCase):
    """Same numbers the demo showed."""

    def test_demo_rule(self):
        self.assertEqual(provisional_price_pounds(150, "مدينة نصر", "sedan", True), 150)
        self.assertEqual(provisional_price_pounds(150, "مدينة نصر", "hatchback", True), 140)  # 135 -> 140
        self.assertEqual(provisional_price_pounds(150, "العبور", "sedan", True), 140)        # 135 -> 140
        self.assertEqual(provisional_price_pounds(150, "العبور", "hatchback", True), 130)    # 140*0.9=126
        self.assertEqual(provisional_price_pounds(150, "مدينتي", "luxury", True), 240)       # 170*1.4=238
        self.assertEqual(provisional_price_pounds(800, "مدينتي", "suv", True), 1060)        # 880*1.2=1056
        # Fixed-price services ignore the size but follow the zone.
        self.assertEqual(provisional_price_pounds(200, "مدينتي", "luxury", False), 220)
        self.assertEqual(provisional_price_pounds(250, "العبور", "suv", False), 230)        # 225 -> 230


class QuoteTests(TestCase):
    def setUp(self):
        self.nasr = Zone.objects.get(name="مدينة نصر")
        self.obour = Zone.objects.get(name="العبور")

    def q(self, codes, zone=None, size="sedan", **kw):
        return build_quote(ids(*codes), zone or self.nasr, size, **kw)

    def test_seed_prices_are_provisional(self):
        self.assertEqual(ServicePrice.objects.count(), 8 * 3 * 4)
        self.assertFalse(ServicePrice.objects.filter(is_provisional=False).exists())
        self.assertTrue(self.q(["exterior-wash"])["has_provisional_prices"])

    def test_single_service(self):
        r = self.q(["exterior-wash"])
        self.assertEqual((r["subtotal"], r["discount"], r["total"], r["total_minutes"]), (15000, 0, 15000, 45))
        self.assertIsNone(r["bundle"])

    def test_basic_bundle_10_percent(self):
        r = self.q(["exterior-wash", "interior-wash"])
        self.assertEqual(r["bundle"]["name"], "الباقة الأساسية")
        self.assertEqual((r["subtotal"], r["discount"], r["total"]), (27000, 2700, 24300))
        self.assertEqual(r["total_minutes"], 85)

    def test_vip_bundle_beats_basic(self):
        r = self.q(["exterior-wash", "interior-wash", "engine-wash", "headlight-restoration"])
        self.assertEqual(r["bundle"]["name"], "باقة VIP")
        # 15% of 670 = 100.50 -> discount rounded DOWN to 100 -> pays 570 (whole pounds).
        self.assertEqual((r["subtotal"], r["discount"], r["total"]), (67000, 10000, 57000))

    def test_bundle_discount_only_on_bundle_services(self):
        r = self.q(["exterior-wash", "interior-wash", "polish-protection"])
        self.assertEqual(r["subtotal"], 27000 + 150000)
        self.assertEqual(r["discount"], 2700)

    def test_detailing_replaces_wash(self):
        r = self.q(["exterior-wash", "exterior-detailing"])
        self.assertEqual([line["code"] for line in r["lines"]], ["exterior-detailing"])
        self.assertEqual(r["removed_services"], ids("exterior-wash"))
        self.assertIn("فشلنا «غسيل خارجي»", r["messages"][0])
        self.assertEqual((r["total"], r["total_minutes"]), (80000, 180))

    def test_replacement_kills_the_bundle(self):
        r = self.q(["exterior-detailing", "exterior-wash", "interior-wash"])
        self.assertIsNone(r["bundle"])
        self.assertEqual(r["total"], 80000 + 12000)

    def test_size_and_zone(self):
        self.assertEqual(self.q(["exterior-wash"], size="suv")["total"], 18000)
        self.assertEqual(self.q(["exterior-wash"], zone=self.obour, size="hatchback")["total"], 13000)
        self.assertEqual(self.q(["engine-wash"], size="luxury")["total"], 20000)  # fixed price
        self.assertEqual(self.q(["exterior-wash"], size="luxury")["total_minutes"], 60)

    def test_shade_warning_or_block(self):
        r = self.q(["polish-protection"], parking="street")
        self.assertEqual(len(r["warnings"]), 1)
        self.assertEqual(self.q(["polish-protection"], parking="closed_garage")["warnings"], [])
        Setting.objects.filter(key="services-block-needs-shade-on-street").update(value=True)
        with self.assertRaises(BusinessError) as e:
            self.q(["polish-protection"], parking="street")
        self.assertEqual(e.exception.detail["code"], "needs_shade")

    def test_oil_line_separate_and_not_discounted(self):
        oil = OilType.objects.create(name="Shell 5W-30 (4 لتر)", price=95000)
        r = self.q(["oil-change"])
        self.assertTrue(r["needs_oil_choice"])
        r = self.q(["oil-change"], oil_type_id=oil.id)
        self.assertFalse(r["needs_oil_choice"])
        self.assertEqual(r["oil"]["price"], 95000)
        self.assertEqual(r["total"], 25000 + 95000)
        with self.assertRaises(BusinessError):
            self.q(["exterior-wash"], oil_type_id=oil.id)

    def test_errors(self):
        for bad in ([], [999999]):
            with self.assertRaises(BusinessError):
                build_quote(bad, self.nasr, "sedan")
        Service.objects.filter(code="engine-wash").update(is_active=False)
        with self.assertRaises(BusinessError):
            self.q(["engine-wash"])
        new_zone = Zone(name="التجمع", polygon=[[29.99, 31.45], [30.04, 31.45], [30.04, 31.52]])
        new_zone.save()
        with self.assertRaises(BusinessError) as e:
            self.q(["exterior-wash"], zone=new_zone)
        self.assertEqual(e.exception.detail["code"], "not_available")

    def test_price_with_piastres_and_no_discount(self):
        ServicePrice.objects.filter(zone=self.nasr, service__code="exterior-wash", size_class="sedan").update(price=16250)
        r = self.q(["exterior-wash"])
        self.assertEqual((r["subtotal"], r["discount"], r["total"]), (16250, 50, 16200))

    def test_every_combination_is_whole_pounds(self):
        """All 255 service combinations x 3 zones x 4 sizes, with odd prices and an oil
        type that has piastres: the total is always whole pounds and never negative."""
        from itertools import combinations
        import random

        rnd = random.Random(3)
        for p in ServicePrice.objects.all():
            p.price = rnd.randint(5000, 200000)  # many with piastres
            p.save()
        oil = OilType.objects.create(name="زيت", price=87550)
        codes = list(Service.objects.values_list("code", flat=True))
        checked = 0
        for zone in Zone.objects.filter(name__in=["مدينة نصر", "العبور", "مدينتي"]):
            for size in ("hatchback", "sedan", "suv", "luxury"):
                for n in range(1, len(codes) + 1):
                    for combo in combinations(codes, n):
                        kw = {"oil_type_id": oil.id} if "oil-change" in combo else {}
                        r = build_quote(ids(*combo), zone, size, **kw)
                        self.assertEqual(r["total"] % 100, 0, (combo, r))
                        self.assertGreaterEqual(r["discount"], 0)
                        self.assertEqual(r["subtotal"] + (r["oil"]["price"] if r["oil"] else 0) - r["discount"],
                                         r["total"])
                        checked += 1
        self.assertEqual(checked, 3 * 4 * 255)

    def test_duplicates_ignored(self):
        self.assertEqual(build_quote(ids("exterior-wash") * 2, self.nasr, "sedan")["total"], 15000)

    def test_inactive_bundle_ignored(self):
        Bundle.objects.update(is_active=False)
        self.assertEqual(self.q(["exterior-wash", "interior-wash"])["discount"], 0)
