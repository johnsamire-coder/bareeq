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
        "key": "scheduling-slot-step-minutes",
        "group": "scheduling",
        "label": "المواعيد اللي بتظهر للعميل كل قد إيه",
        "description": "30 يعني 9:00، 9:30، 10:00...",
        "value_type": "minutes",
        "value": 30,
    },
    {
        "key": "scheduling-min-notice-minutes",
        "group": "scheduling",
        "label": "أقرب ميعاد يتحجز بعد دلوقتي بـ",
        "description": "مثلاً 60: لو الساعة 2، أقرب ميعاد يظهر 3.",
        "value_type": "minutes",
        "value": 60,
    },
    {
        "key": "scheduling-days-ahead",
        "group": "scheduling",
        "label": "العميل يقدر يحجز لحد كام يوم قدام",
        "description": "",
        "value_type": "days",
        "value": 7,
    },
    {
        "key": "travel-speed-kmh",
        "group": "scheduling",
        "label": "متوسط سرعة الفني في الطريق (كيلو في الساعة)",
        "description": "لحساب وقت السكة التقريبي، لحد ما نستخدم جوجل ماب.",
        "value_type": "integer",
        "value": 25,
    },
    {
        "key": "travel-road-factor-percent",
        "group": "scheduling",
        "label": "المسافة في الشوارع أطول من الخط المستقيم بنسبة (%)",
        "description": "140 يعني المسافة × 1.4. لحساب وقت السكة التقريبي، لحد ما نستخدم جوجل ماب.",
        "value_type": "integer",
        "value": 140,
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
        "label": "رسوم الإلغاء أو التأجيل المتأخر",
        "description": "",
        "value_type": "money",
        "value": 5000,
        "mentioned_in_terms": True,
    },
    {
        "key": "car-not-found-fee",
        "group": "cancellation",
        "label": "رسوم «الفني وصل وملقاش العربية»",
        "description": "",
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
    # Before/after photos: checks that mark a photo as doubtful (it is still kept).
    {
        "key": "photos-max-age-minutes",
        "group": "photos",
        "label": "الصورة تتعلّم لو اتصورت قبل رفعها بأكتر من",
        "description": "علامة بس، الصورة بتتحفظ. بتساعد تكشف الصور القديمة.",
        "value_type": "minutes",
        "value": 10,
    },
    {
        "key": "photos-max-distance-meters",
        "group": "photos",
        "label": "الصورة تتعلّم لو اتصورت بعيد عن العنوان بأكتر من (متر)",
        "description": "علامة بس، الصورة بتتحفظ.",
        "value_type": "integer",
        "value": 300,
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
    # Services (SPEC section 5)
    {
        "key": "services-block-needs-shade-on-street",
        "group": "services",
        "label": "منع خدمات «محتاجة ضل» لو العربية في الشارع",
        "description": "لو «لا»: التطبيق بينبه العميل بس. لو «نعم»: بيمنعه يطلبها.",
        "value_type": "boolean",
        "value": False,
    },
    # Payments (SPEC section 8)
    {
        "key": "instapay-payment-details",
        "group": "payments",
        "label": "بيانات InstaPay اللي بتظهر للعميل",
        "description": "اسم المستخدم أو الرقم أو اللينك اللي العميل يحوّل عليه.",
        "value_type": "text",
        "value": "[مؤقت] بيانات حساب InstaPay لسه هتتحط. من فضلك ماتحوّلش فلوس دلوقتي واختار الدفع كاش.",
    },
    # Online payments (phase 3)
    {
        "key": "card-payment-enabled",
        "group": "payments",
        "label": "الدفع بالكارت ومحافظ الموبايل شغال",
        "description": "",
        "value_type": "boolean",
        "value": True,
    },
    {
        "key": "card-payment-hold-extra-minutes",
        "group": "payments",
        "label": "وقت زيادة للحجز المؤقت وصفحة الدفع مفتوحة",
        "description": "عشان الميعاد ميروحش وهو بيكتب بيانات الكارت.",
        "value_type": "minutes",
        "value": 15,
    },
    {
        "key": "card-refund-auto-after-hours",
        "group": "payments",
        "label": "فلوس الكارت ترجع لوحدها بعد",
        "description": "لو الطلب المدفوع بالكارت اتلغى والعميل ماختارش المحفظة.",
        "value_type": "hours",
        "value": 24,
    },
    # Monthly subscription (phase 3)
    {
        "key": "subscriptions-enabled",
        "group": "subscriptions",
        "label": "الاشتراك الشهري شغال",
        "description": "",
        "value_type": "boolean",
        "value": True,
    },
    {
        "key": "subscription-renewal-reminder-days",
        "group": "subscriptions",
        "label": "تذكير التجديد قبل نهاية الشهر بـ",
        "description": "",
        "value_type": "days",
        "value": 3,
    },
    {
        "key": "subscription-makeup-extra-days",
        "group": "subscriptions",
        "label": "زيارة الشركة لغتها تتعوض لحد كام يوم بعد الشهر",
        "description": "",
        "value_type": "days",
        "value": 7,
    },
    # Phase 4 (numbers agreed with John 19 Nov 2026)
    {
        "key": "express-enabled",
        "group": "fees",
        "label": "الطلب السريع («عايز حد دلوقتي») شغال",
        "description": "",
        "value_type": "boolean",
        "value": True,
    },
    {
        "key": "express-fee",
        "group": "fees",
        "label": "رسوم الطلب السريع",
        "description": "",
        "value_type": "money",
        "value": 5000,
    },
    {
        "key": "express-time-step-minutes",
        "group": "fees",
        "label": "الطلب السريع: المواعيد كل كام دقيقة",
        "description": "",
        "value_type": "minutes",
        "value": 5,
    },
    {
        "key": "distance-fee-free-km",
        "group": "fees",
        "label": "رسوم المسافة: ببلاش لحد كام كيلو من أقرب فني",
        "description": "المسافة في خط مستقيم لحد ما خريطة جوجل تيجي.",
        "value_type": "integer",
        "value": 10,
    },
    {
        "key": "distance-fee-per-km",
        "group": "fees",
        "label": "رسوم المسافة: لكل كيلو زيادة",
        "description": "",
        "value_type": "money",
        "value": 500,
    },
    {
        "key": "distance-fee-max",
        "group": "fees",
        "label": "رسوم المسافة: أقصى حاجة",
        "description": "",
        "value_type": "money",
        "value": 5000,
    },
    {
        "key": "tracking-interval-seconds",
        "group": "tracking",
        "label": "الفني بيبعت مكانه كل كام ثانية",
        "description": "من «في الطريق» لحد «وصل» بس.",
        "value_type": "integer",
        "value": 30,
    },
    {
        "key": "tracking-keep-days",
        "group": "tracking",
        "label": "أماكن الفنيين بتتمسح بعد",
        "description": "",
        "value_type": "days",
        "value": 7,
    },
    {
        "key": "tracking-fresh-minutes",
        "group": "tracking",
        "label": "خريطة المدير: المكان يبان لو أحدث من",
        "description": "",
        "value_type": "minutes",
        "value": 15,
    },
    {
        "key": "reports-on-time-grace-minutes",
        "group": "tracking",
        "label": "التقارير: الفني «في ميعاده» لو بدأ متأخر لحد",
        "description": "",
        "value_type": "minutes",
        "value": 15,
    },
    # VAT: off for now; invoices are issued without tax.
    {
        "key": "vat-enabled",
        "group": "payments",
        "label": "تطبيق ضريبة القيمة المضافة",
        "description": "مقفول دلوقتي: الأسعار والفاتورة من غير ضريبة.",
        "value_type": "boolean",
        "value": False,
    },
    {
        "key": "vat-percent",
        "group": "payments",
        "label": "نسبة ضريبة القيمة المضافة",
        "description": "فاضية لحد ما نعرفها من المحاسب.",
        "value_type": "percent",
        "value": None,
        "allow_empty": True,
    },
    # Test mode (must be switched off before launch)
    {
        "key": "demo-mode",
        "group": "login",
        "label": "وضع تجربة",
        "description": "لما يبقى شغال: كود الدخول بيظهر على شاشة الدخول نفسها (من غير رسايل)، "
                       "وفوق في التطبيق شريط «نسخة تجريبية». لازم يتقفل قبل الإطلاق.",
        "value_type": "boolean",
        "value": True,
    },
    # Loyalty and rewards (phase 2, SPEC section 11; starting values agreed with John 19 Nov 2026).
    # Only ONE extra discount per order (coupon / wash card / referral): the biggest.
    {
        "key": "cashback-enabled",
        "group": "loyalty",
        "label": "الكاش باك شغال",
        "description": "نسبة من اللي العميل دفعه فلوس بتنزل في محفظته بعد ما الطلب يخلص.",
        "value_type": "boolean",
        "value": False,
    },
    {
        "key": "cashback-percent",
        "group": "loyalty",
        "label": "نسبة الكاش باك",
        "description": "من اللي اتدفع كاش أو InstaPay بس (مش من المحفظة).",
        "value_type": "percent",
        "value": 5,
    },
    {
        "key": "wash-card-enabled",
        "group": "loyalty",
        "label": "كارت الغسيل شغال",
        "description": "كل عدد معين من الطلبات اللي خلصت، الطلب اللي بعده بخصم.",
        "value_type": "boolean",
        "value": True,
    },
    {
        "key": "wash-card-every-n",
        "group": "loyalty",
        "label": "كارت الغسيل: كل كام طلب",
        "description": "5 يعني بعد 5 طلبات خلصوا، الطلب السادس عليه الخصم. الطلب بيتحسب مرة واحدة حتى لو فيه كذا عربية.",
        "value_type": "integer",
        "value": 5,
    },
    {
        "key": "wash-card-reward-percent",
        "group": "loyalty",
        "label": "كارت الغسيل: نسبة الخصم",
        "description": "على الخدمات بس (مش الزيت). 100 يعني الطلب ببلاش.",
        "value_type": "percent",
        "value": 50,
    },
    {
        "key": "referral-enabled",
        "group": "loyalty",
        "label": "الدعوة (كود الصاحب) شغالة",
        "description": "",
        "value_type": "boolean",
        "value": True,
    },
    {
        "key": "referral-new-customer-discount",
        "group": "loyalty",
        "label": "خصم أول طلب للعميل المدعو",
        "description": "",
        "value_type": "money",
        "value": 5000,
    },
    {
        "key": "referral-referrer-credit",
        "group": "loyalty",
        "label": "رصيد صاحب الكود",
        "description": "بينزل في محفظته بعد ما صاحبه يخلص أول طلب مدفوع.",
        "value_type": "money",
        "value": 5000,
    },
    {
        "key": "referral-monthly-cap",
        "group": "loyalty",
        "label": "أقصى عدد مكافآت دعوة للعميل في الشهر",
        "description": "اللي فوقه بيروح للمدير يوافق أو يرفض.",
        "value_type": "integer",
        "value": 5,
    },
    {
        "key": "refund-to-wallet-bonus-percent",
        "group": "loyalty",
        "label": "زيادة لو العميل اختار الفلوس ترجع للمحفظة",
        "description": "لما طلب مدفوع InstaPay يتلغي، والعميل يختار المحفظة بدل ما الفلوس ترجعله.",
        "value_type": "percent",
        "value": 10,
    },
    {
        "key": "winback-after-days",
        "group": "loyalty",
        "label": "إشعار «وحشتنا» بعد كام يوم من غير طلب",
        "description": "",
        "value_type": "days",
        "value": 30,
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
    {
        "key": "notifications-reminder-minutes-before",
        "group": "notifications",
        "label": "تذكير العميل قبل الميعاد بـ",
        "description": "",
        "value_type": "minutes",
        "value": 60,
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
        "key": "google-maps-review-link",
        "group": "ratings",
        "label": "لينك تقييم بريق على جوجل ماب",
        "description": "بيظهر للعميل لما يدي 5 نجوم (من غير أي مكافأة).",
        "value_type": "text",
        "value": "[مؤقت] لينك تقييم جوجل ماب لسه هيتحط.",
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
        if any(k not in columns for k in item if k != "key"):
            continue  # needs a newer table; a later migration adds it
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
