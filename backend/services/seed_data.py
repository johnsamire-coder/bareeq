"""Starting services, PROVISIONAL prices and ESTIMATED durations.

Prices follow the old demo (design/demo/index.html), as John asked:
- Base = Nasr City, sedan (in pounds).
- Zone: Obour -10%, Madinaty +10% (rounded to the nearest 10 pounds).
- Size, for wash/detail/polish services only: hatchback -10%, SUV +20%,
  luxury +40% (rounded to the nearest 10 pounds).
- Engine wash, headlights and oil change: same price for every size.
All prices are marked provisional until the manager confirms them.
"""

H, S, U, L = "hatchback", "sedan", "suv", "luxury"
SIZES = [H, S, U, L]

ZONE_FACTORS = {"مدينة نصر": 1.0, "العبور": 0.9, "مدينتي": 1.1}
SIZE_FACTORS = {H: 0.9, S: 1.0, U: 1.2, L: 1.4}

# code, name, description, category, base price (pounds, Nasr City sedan),
# price depends on size, needs shade, oil change, minutes by size {H, S, U, L}
SERVICES = [
    ("exterior-wash", "غسيل خارجي", "رغوة وشطف وتنشيف وشمع سريع", "wash", 150, True, False, False,
     {H: 35, S: 45, U: 55, L: 60}),
    ("interior-wash", "غسيل داخلي", "شفط وتنضيف التابلوه والزجاج من جوه", "wash", 120, True, False, False,
     {H: 30, S: 40, U: 50, L: 55}),
    ("engine-wash", "غسيل موتور", "بالبخار ومواد آمنة على الكهربا", "wash", 200, False, False, False,
     {H: 30, S: 30, U: 30, L: 30}),
    ("exterior-detailing", "ديتيلنج خارجي", "إزالة الشوائب وتلميع البوية، وبيشمل الغسيل الخارجي", "detail", 800,
     True, True, False, {H: 150, S: 180, U: 210, L: 240}),
    ("interior-detailing", "ديتيلنج داخلي", "غسيل الفرش والسقف وتعقيم، وبيشمل الغسيل الداخلي", "detail", 900,
     True, False, False, {H: 150, S: 180, U: 210, L: 240}),
    ("polish-protection", "تلميع وحماية بالواكس", "طبقة حماية ولمعان بيستمر أسابيع", "detail", 1500, True, True,
     False, {H: 75, S: 90, U: 110, L: 120}),
    ("headlight-restoration", "تلميع الفوانيس", "بيرجّع وضوح الفانوس الأمامي", "extra", 200, False, False, False,
     {H: 30, S: 30, U: 30, L: 30}),
    ("oil-change", "تغيير زيت وفلتر", "المصنعية بس، والزيت بيتحسب لوحده حسب النوع اللي تختاره", "extra", 250, False,
     False, True, {H: 30, S: 30, U: 30, L: 30}),
]

REPLACES = [("exterior-detailing", "exterior-wash"), ("interior-detailing", "interior-wash")]

BUNDLES = [
    ("الباقة الأساسية", "غسيل خارجي + داخلي", ["exterior-wash", "interior-wash"], 10),
    ("باقة VIP", "خارجي + داخلي + موتور + فوانيس",
     ["exterior-wash", "interior-wash", "engine-wash", "headlight-restoration"], 15),
]


def round10(pounds):
    """Same rounding as the demo: nearest 10 pounds, halves up."""
    return int((pounds + 5) // 10 * 10)


def provisional_price_pounds(base, zone_name, size, depends_on_size):
    zone_price = round10(base * ZONE_FACTORS[zone_name])
    return round10(zone_price * SIZE_FACTORS[size]) if depends_on_size else zone_price


def seed_services(Service, ServicePrice, ServiceDuration, Bundle, Zone):
    if Service.objects.exists():
        return
    by_code = {}
    for i, (code, name, desc, cat, base, by_size, shade, oil, mins) in enumerate(SERVICES):
        s = Service.objects.create(
            code=code, name=name, description=desc, category=cat, price_depends_on_size=by_size,
            needs_shade=shade, is_oil_change=oil, sort_order=i,
        )
        by_code[code] = (s, base, by_size)
        for size in SIZES:
            ServiceDuration.objects.create(service=s, size_class=size, minutes=mins[size])
    for code, replaced in REPLACES:
        by_code[code][0].replaces.add(by_code[replaced][0])
    for zone in Zone.objects.filter(name__in=ZONE_FACTORS):
        for s, base, by_size in by_code.values():
            for size in SIZES:
                pounds = provisional_price_pounds(base, zone.name, size, by_size)
                ServicePrice.objects.create(
                    service=s, zone=zone, size_class=size, price=pounds * 100, is_provisional=True
                )
    for i, (name, desc, codes, pct) in enumerate(BUNDLES):
        b = Bundle.objects.create(name=name, description=desc, discount_percent=pct, sort_order=i)
        b.services.set([by_code[c][0] for c in codes])
