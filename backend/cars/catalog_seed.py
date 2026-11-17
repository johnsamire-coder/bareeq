"""Starting car catalog: brands and models common in Egypt, each model with its size.

Only used to fill an empty catalog the first time. After that the manager
reviews and edits brands and models from the manager screens in the app.
Sizes: H = hatchback, S = sedan, U = SUV (incl. pick-ups and 7-seaters), L = luxury.
"""

H, S, U, L = "hatchback", "sedan", "suv", "luxury"

# (name_en, name_ar, [(model, size), ...])
CATALOG = [
    # Japanese / Korean
    ("Toyota", "تويوتا", [
        ("Corolla", S), ("Yaris", H), ("Yaris Sedan", S), ("Belta", S), ("Camry", S), ("Avanza", U),
        ("Rush", U), ("Raize", U), ("C-HR", U), ("Corolla Cross", U), ("RAV4", U), ("Fortuner", U),
        ("Hilux", U), ("Land Cruiser", U), ("Land Cruiser Prado", U),
    ]),
    ("Hyundai", "هيونداي", [
        ("Accent", S), ("Accent RB", S), ("Verna", S), ("Elantra", S), ("Elantra HD", S), ("Elantra AD", S),
        ("Sonata", S), ("Getz", H), ("i10", H), ("Grand i10", H), ("i20", H), ("i30", H), ("Matrix", H),
        ("Venue", U), ("Bayon", U), ("Creta", U), ("Kona", U), ("Tucson", U), ("Santa Fe", U),
    ]),
    ("Kia", "كيا", [
        ("Picanto", H), ("Rio", H), ("Soul", H), ("Pegas", S), ("Cerato", S), ("Optima", S), ("K5", S),
        ("Sonet", U), ("Seltos", U), ("Carens", U), ("Sportage", U), ("Sorento", U),
    ]),
    ("Nissan", "نيسان", [
        ("Sunny", S), ("Sentra", S), ("Tiida", H), ("Kicks", U), ("Juke", U), ("Qashqai", U),
        ("X-Trail", U), ("Patrol", U),
    ]),
    ("Mitsubishi", "ميتسوبيشي", [
        ("Mirage", H), ("Attrage", S), ("Lancer", S), ("Xpander", U), ("Eclipse Cross", U),
        ("Outlander", U), ("Pajero", U),
    ]),
    ("Suzuki", "سوزوكي", [
        ("Alto", H), ("Celerio", H), ("S-Presso", H), ("Swift", H), ("Dzire", S), ("Ciaz", S),
        ("Ertiga", U), ("Vitara", U), ("Jimny", U),
    ]),
    ("Honda", "هوندا", [("City", S), ("Civic", S), ("Accord", S), ("HR-V", U), ("CR-V", U)]),
    ("Mazda", "مازدا", [("Mazda 2", H), ("Mazda 3", S), ("Mazda 6", S), ("CX-3", U), ("CX-30", U), ("CX-5", U)]),
    ("Subaru", "سوبارو", [("Impreza", S), ("XV", U), ("Forester", U)]),
    # Chinese
    ("Chery", "شيري", [
        ("QQ", H), ("Arrizo 5", S), ("Envy", S), ("Tiggo 2", U), ("Tiggo 3", U), ("Tiggo 4", U),
        ("Tiggo 4 Pro", U), ("Tiggo 7", U), ("Tiggo 7 Pro", U), ("Tiggo 8", U), ("Tiggo 8 Pro", U),
    ]),
    ("MG", "إم جي", [
        ("MG 3", H), ("MG 4", H), ("MG 5", S), ("MG 6", S), ("ZS", U), ("HS", U), ("RX5", U), ("RX8", U),
    ]),
    ("Geely", "جيلي", [
        ("Pandino", H), ("Emgrand", S), ("Emgrand 7", S), ("Coolray", U), ("Okavango", U), ("Tugella", U),
        ("Monjaro", U),
    ]),
    ("BYD", "بي واي دي", [
        ("F0", H), ("F3", S), ("L3", S), ("Dolphin", H), ("Seal", S), ("Song", U), ("Atto 3", U), ("Tang", U),
    ]),
    ("Jetour", "جيتور", [("X50", U), ("X70", U), ("X70 Plus", U), ("X90", U), ("Dashing", U), ("T2", U)]),
    ("Haval", "هافال", [("H2", U), ("Jolion", U), ("H6", U), ("Dargo", U), ("H9", U)]),
    ("Changan", "شانجان", [
        ("Alsvin", S), ("Eado", S), ("CS35", U), ("CS35 Plus", U), ("CS75", U), ("UNI-K", U), ("UNI-T", U),
    ]),
    ("Speranza", "سبرانزا", [("A113", H), ("A516", S), ("A620", S), ("Tiggo", U)]),
    ("Brilliance", "بريليانس", [("FRV", H), ("Splendor", S), ("Galena", S), ("H530", S), ("V5", U)]),
    ("BAIC", "بايك", [("U5 Plus", S), ("X3", U), ("X35", U), ("X7", U)]),
    ("Senova", "سينوفا", [("D20", H), ("X25", U)]),
    ("Dongfeng", "دونج فينج", [("Aeolus A30", S), ("Shine", S), ("AX7", U)]),
    ("JAC", "جاك", [("J7", S), ("S3", U), ("JS4", U)]),
    ("Kaiyi", "كايي", [("X3 Pro", U), ("X7", U)]),
    ("Bestune", "بيستون", [("B70", S), ("T77", U)]),
    ("GAC", "جي إيه سي", [("GA4", S), ("GS3", U), ("Emzoom", U), ("GS8", U)]),
    ("Exeed", "إكسيد", [("LX", U), ("TXL", U), ("VX", U)]),
    # European / American (mainstream)
    ("Chevrolet", "شيفروليه", [
        ("Spark", H), ("Lanos", S), ("Aveo", S), ("Optra", S), ("Cruze", S), ("Groove", U), ("Captiva", U),
        ("Trailblazer", U), ("Tahoe", U),
    ]),
    ("Daewoo", "دايو", [("Matiz", H), ("Lanos", S), ("Nubira", S)]),
    ("Renault", "رينو", [
        ("Sandero", H), ("Sandero Stepway", H), ("Logan", S), ("Taliant", S), ("Fluence", S), ("Megane", S),
        ("Captur", U), ("Duster", U), ("Kadjar", U), ("Austral", U),
    ]),
    ("Peugeot", "بيجو", [("208", H), ("301", S), ("408", S), ("508", S), ("2008", U), ("3008", U), ("5008", U)]),
    ("Citroen", "ستروين", [("C3", H), ("C4", H), ("C-Elysee", S), ("C4 X", S), ("C5 Aircross", U)]),
    ("Opel", "أوبل", [
        ("Corsa", H), ("Astra", H), ("Vectra", S), ("Insignia", S), ("Crossland", U), ("Mokka", U),
        ("Grandland", U),
    ]),
    ("Skoda", "سكودا", [
        ("Fabia", H), ("Scala", H), ("Rapid", S), ("Octavia", S), ("Superb", S), ("Kamiq", U), ("Karoq", U),
        ("Kodiaq", U),
    ]),
    ("Volkswagen", "فولكس فاجن", [
        ("Polo", H), ("Golf", H), ("Jetta", S), ("Passat", S), ("T-Roc", U), ("Tiguan", U), ("Touareg", U),
    ]),
    ("Seat", "سيات", [("Ibiza", H), ("Leon", H), ("Toledo", S), ("Arona", U), ("Ateca", U), ("Tarraco", U)]),
    ("Fiat", "فيات", [("Uno", H), ("Punto", H), ("500", H), ("128", S), ("Linea", S), ("Tipo", S)]),
    ("Ford", "فورد", [("Fiesta", H), ("Focus", S), ("EcoSport", U), ("Kuga", U), ("Explorer", U)]),
    ("Jeep", "جيب", [("Renegade", U), ("Compass", U), ("Cherokee", U), ("Grand Cherokee", U), ("Wrangler", U)]),
    ("Lada", "لادا", [("2107", S), ("Granta", S), ("Vesta", S), ("Largus", U), ("Niva", U)]),
    ("Proton", "بروتون", [("Gen-2", H), ("Saga", S), ("Persona", S), ("X50", U), ("X70", U)]),
    ("Mini", "ميني", [("Cooper", H), ("Countryman", U)]),
    # Luxury
    ("Mercedes-Benz", "مرسيدس", [
        ("A-Class", L), ("CLA", L), ("C-Class", L), ("E-Class", L), ("S-Class", L), ("GLA", L), ("GLC", L),
        ("GLE", L), ("GLS", L), ("G-Class", L),
    ]),
    ("BMW", "بي إم دبليو", [
        ("1 Series", L), ("2 Series", L), ("3 Series", L), ("5 Series", L), ("7 Series", L), ("X1", L),
        ("X3", L), ("X5", L), ("X6", L), ("X7", L),
    ]),
    ("Audi", "أودي", [("A3", L), ("A4", L), ("A6", L), ("A8", L), ("Q2", L), ("Q3", L), ("Q5", L), ("Q7", L), ("Q8", L)]),
    ("Lexus", "لكزس", [("IS", L), ("ES", L), ("NX", L), ("RX", L), ("LX", L)]),
    ("Land Rover", "لاند روفر", [
        ("Range Rover", L), ("Range Rover Sport", L), ("Range Rover Velar", L), ("Range Rover Evoque", L),
        ("Discovery", L), ("Discovery Sport", L), ("Defender", L),
    ]),
    ("Volvo", "فولفو", [("S60", L), ("S90", L), ("XC40", L), ("XC60", L), ("XC90", L)]),
    ("Jaguar", "جاكوار", [("XE", L), ("XF", L), ("F-Pace", L)]),
    ("Porsche", "بورشه", [("Macan", L), ("Cayenne", L), ("Panamera", L), ("911", L)]),
]

# (name, hex)
COLORS = [
    ("أبيض", "#FFFFFF"), ("أسود", "#000000"), ("فضي", "#C0C0C0"), ("رمادي", "#808080"),
    ("أحمر", "#C62828"), ("نبيتي", "#6D1A2A"), ("أزرق", "#1E5BC6"), ("كحلي", "#1B2A4A"),
    ("لبني", "#8EC9E8"), ("أخضر", "#2E7D32"), ("بني", "#6D4C41"), ("بيج", "#D8C8A8"),
    ("شمبانيا", "#E5D3B3"), ("دهبي", "#C9A227"), ("برتقالي", "#EF6C00"), ("أصفر", "#F9D71C"),
]


def seed_catalog(Brand, Model, Color):
    """Fill the catalog only when it is empty (never touches manager edits)."""
    if not Brand.objects.exists():
        for i, (name_en, name_ar, models) in enumerate(CATALOG):
            brand = Brand.objects.create(name_en=name_en, name_ar=name_ar, sort_order=i)
            for name, size in models:
                Model.objects.create(brand=brand, name=name, size_class=size)
    if not Color.objects.exists():
        for i, (name, hex_code) in enumerate(COLORS):
            Color.objects.create(name=name, hex_code=hex_code, sort_order=i)
