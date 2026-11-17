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
    created = 0
    for item in DEFAULT_SETTINGS:
        _, was_created = SettingModel.objects.get_or_create(
            key=item["key"], defaults={k: v for k, v in item.items() if k != "key"}
        )
        created += int(was_created)
    return created
