"""Starting values for the settings table.

These are only written when a key does not exist yet; the manager's edits
are never overwritten. Values come from docs/SPEC.md.
"""

DEFAULT_SETTINGS = [
    # Scheduling (SPEC section 6)
    {
        "key": "scheduling-buffer-minutes",
        "group": "scheduling",
        "label": "وقت احتياطي بين كل طلب والتاني",
        "description": "دقايق بتتزود بعد وقت السكة قبل الطلب اللي بعده.",
        "value_type": "minutes",
        "value": 15,
    },
    {
        "key": "scheduling-min-gap-minutes",
        "group": "scheduling",
        "label": "أقل فرق بين بداية طلبين لنفس الفني",
        "description": "من بداية الطلب لبداية اللي بعده، مهما كان الطلب قصير.",
        "value_type": "minutes",
        "value": 90,
    },
    {
        "key": "scheduling-slot-hold-minutes",
        "group": "scheduling",
        "label": "مدة حجز الميعاد مؤقتاً لحد الدفع",
        "description": "لو العميل مكملش الدفع في المدة دي، الميعاد بيرجع متاح.",
        "value_type": "minutes",
        "value": 10,
    },
    {
        "key": "scheduling-express-max-arrival-minutes",
        "group": "scheduling",
        "label": "الطلب السريع: أقصى وقت للوصول",
        "description": "الطلب السريع بيظهر بس لو فيه فني يقدر يوصل في المدة دي (المرحلة 4).",
        "value_type": "minutes",
        "value": 90,
    },
    # Login with one-time code (SPEC section 2)
    {
        "key": "otp-code-valid-minutes",
        "group": "login",
        "label": "مدة صلاحية كود الدخول",
        "description": "بعد المدة دي الكود مايشتغلش، والعميل يطلب كود جديد.",
        "value_type": "minutes",
        "value": 5,
    },
    {
        "key": "otp-max-requests-per-phone-per-hour",
        "group": "login",
        "label": "أقصى عدد أكواد لنفس الرقم في الساعة",
        "description": "",
        "value_type": "integer",
        "value": 5,
    },
    {
        "key": "otp-max-requests-per-device-per-hour",
        "group": "login",
        "label": "أقصى عدد أكواد لنفس الموبايل (الجهاز) في الساعة",
        "description": "عشان محدش يجرب أرقام كتير من نفس الجهاز.",
        "value_type": "integer",
        "value": 5,
    },
    {
        "key": "otp-max-wrong-attempts",
        "group": "login",
        "label": "أقصى عدد محاولات كود غلط",
        "description": "بعدها الكود يتقفل والعميل يطلب كود جديد.",
        "value_type": "integer",
        "value": 5,
    },
    # Cancellation (SPEC section 7). These numbers are written in the terms text.
    {
        "key": "cancellation-free-until-hours",
        "group": "cancellation",
        "label": "الإلغاء أو التأجيل ببلاش لحد قبل الميعاد بـ",
        "description": "بعد كده بتتحسب رسوم الإلغاء المتأخر.",
        "value_type": "hours",
        "value": 2,
        "mentioned_in_terms": True,
    },
    {
        "key": "cancellation-late-fee",
        "group": "cancellation",
        "label": "رسوم الإلغاء أو التأجيل المتأخر (بالقرش)",
        "description": "5000 قرش = 50 جنيه.",
        "value_type": "money",
        "value": 5000,
        "mentioned_in_terms": True,
    },
    {
        "key": "car-not-found-fee",
        "group": "cancellation",
        "label": "رسوم «الفني وصل وملقاش العربية» (بالقرش)",
        "description": "5000 قرش = 50 جنيه.",
        "value_type": "money",
        "value": 5000,
        "mentioned_in_terms": True,
    },
    {
        "key": "car-not-found-wait-minutes",
        "group": "cancellation",
        "label": "الفني يستنى قد إيه قبل «العربية مش موجودة»",
        "description": "بعد ما الفني يتصل بالعميل. زرار «العربية مش موجودة» بيشتغل بعد المدة دي.",
        "value_type": "minutes",
        "value": 15,
        "mentioned_in_terms": True,
    },
    {
        "key": "damage-report-within-hours",
        "group": "cancellation",
        "label": "مدة الإبلاغ عن ضرر بعد خلاص الغسلة",
        "description": "بعد المدة دي التطبيق مبيقبلش بلاغ ضرر للطلب ده.",
        "value_type": "hours",
        "value": 24,
        "mentioned_in_terms": True,
    },
    # Cars (SPEC section 3)
    {
        "key": "cars-first-year",
        "group": "cars",
        "label": "أقدم سنة صنع في القايمة",
        "description": "",
        "value_type": "integer",
        "value": 1990,
    },
    {
        "key": "cars-years-ahead",
        "group": "cars",
        "label": "سنين بعد السنة الحالية في القايمة",
        "description": "1 يعني القايمة بتوصل لحد السنة الجاية.",
        "value_type": "integer",
        "value": 1,
    },
    # Wallet (SPEC section 11)
    {
        "key": "wallet-max-order-share-percent",
        "group": "wallet",
        "label": "أقصى نسبة من الطلب تتدفع من المحفظة",
        "description": "",
        "value_type": "percent",
        "value": 50,
    },
    {
        "key": "wallet-credit-expiry-days",
        "group": "wallet",
        "label": "صلاحية الرصيد",
        "description": "كل رصيد بيدخل المحفظة بينتهي بعد عدد الأيام ده.",
        "value_type": "days",
        "value": 90,
    },
    {
        "key": "wallet-expiry-reminder-days",
        "group": "wallet",
        "label": "تنبيه قبل انتهاء الرصيد",
        "description": "نبعت للعميل تنبيه قبل ما الرصيد يخلص بعدد الأيام ده.",
        "value_type": "days",
        "value": 7,
    },
    # Notifications (SPEC section 9)
    {
        "key": "notifications-next-wash-after-days",
        "group": "notifications",
        "label": "تذكير «وقت الغسلة الجاية»",
        "description": "بعد عدد الأيام ده من آخر غسلة.",
        "value_type": "days",
        "value": 14,
    },
    # Ratings (SPEC section 10)
    {
        "key": "ratings-bad-max-stars",
        "group": "ratings",
        "label": "التقييم السيئ: عدد النجوم أو أقل",
        "description": "التقييم ده أو أقل بيبعت تنبيه فوري للمدير.",
        "value_type": "integer",
        "value": 3,
    },
    {
        "key": "ratings-reminder-after-hours",
        "group": "ratings",
        "label": "تذكير بالتقييم بعد",
        "description": "لو العميل مقيّمش بعد عدد الساعات ده، نفكره مرة واحدة.",
        "value_type": "hours",
        "value": 24,
    },
]


def seed_default_settings(SettingModel):
    """Create any missing default settings. Returns the number created."""
    # Older migrations call this with an older version of the table, so only
    # pass the columns that exist at that point.
    columns = {f.name for f in SettingModel._meta.get_fields()}
    created = 0
    for item in DEFAULT_SETTINGS:
        _, was_created = SettingModel.objects.get_or_create(
            key=item["key"], defaults={k: v for k, v in item.items() if k != "key" and k in columns}
        )
        created += int(was_created)
        # "Written in the terms" is decided by us, not the manager: always keep it in sync.
        if "mentioned_in_terms" in columns:
            SettingModel.objects.filter(key=item["key"]).update(
                mentioned_in_terms=item.get("mentioned_in_terms", False)
            )
    return created
