"""All the messages the system sends. Called from the places where things happen."""
from scheduling.availability import CAIRO

from .service import notify, notify_managers


def _when(order):
    """e.g. '18/11 الساعة 3:30 م' (12-hour clock with morning/evening)."""
    t = order.scheduled_start.astimezone(CAIRO)
    hour = t.hour % 12 or 12
    return f"{t:%d/%m} الساعة {hour}:{t:%M} {'ص' if t.hour < 12 else 'م'}"


def welcome(user):
    notify(user, "welcome", "أهلاً بيك في بريق", "حسابك اتعمل. ضيف عربيتك وعنوانك واحجز أول غسلة.")


def booking_confirmed(order):
    notify(order.customer, "booking_confirmed", "الحجز اتأكد", f"ميعادك {_when(order)}.", {"order": order.id})


def instapay_to_review(order):
    notify_managers("instapay_to_review", "تحويل InstaPay محتاج مراجعة",
                    f"طلب {order.id}: راجع صورة التحويل وأكد.", {"order": order.id})


def booking_reminder(order):
    notify(order.customer, "booking_reminder", "فاضل ساعة على ميعادك",
           f"الفني جايلك {_when(order)}. اتأكد إن العربية في مكانها.", {"order": order.id},
           dedupe_key=f"booking-reminder:{order.id}")


def technician_on_the_way(order):
    notify(order.customer, "technician_on_the_way", "الفني في الطريق",
           f"{order.technician.full_name} في الطريق ليك.", {"order": order.id})


def technician_changed(order):
    notify(order.customer, "technician_changed", "اتغير الفني",
           f"الفني بتاع طلبك {_when(order)} بقى {order.technician.full_name}.", {"order": order.id})


def job_done(order):
    notify(order.customer, "job_done", "عربيتك خلصت", "قيّم الخدمة وقولنا رأيك.", {"order": order.id, "action": "rate"})


def rating_reminder(order):
    notify(order.customer, "rating_reminder", "رأيك يهمنا", "لسه مقيّمتش آخر غسلة.",
           {"order": order.id, "action": "rate"}, dedupe_key=f"rating-reminder:{order.id}")


def car_not_found(order):
    notify(order.customer, "car_not_found", "الفني ملقاش العربية",
           "الفني وصل واستنى ومقدرش يوصل للعربية، والطلب اتلغى.", {"order": order.id})
    notify_managers("car_not_found", "عربية مش موجودة", f"طلب {order.id}: الفني سجل إن العربية مش موجودة.",
                    {"order": order.id})


def day_closed(order, reason):
    notify(order.customer, "day_closed", "اتلغى ميعادك",
           f"اتلغى ميعادك {_when(order)} بسبب: {reason}. مفيش عليك أي رسوم، احجز ميعاد جديد.",
           {"order": order.id, "action": "rebook"})


def wallet_credit(entry):
    pounds = f"{entry.amount / 100:g}"
    title, body = "رصيد جديد في محفظتك", f"اتضاف {pounds} جنيه لمحفظتك."
    if entry.kind == "cashback":
        title, body = "نزلك كاش باك", f"اتضاف {pounds} جنيه كاش باك من طلبك لمحفظتك."
    elif entry.kind == "referral":
        title, body = "صاحبك جرّب بريق", f"صاحبك خلص أول غسلة، ونزلك {pounds} جنيه في محفظتك. شكراً إنك عرّفته علينا."
    notify(entry.customer, "wallet_credit", title, body, {"wallet_entry": entry.id})


def wallet_expiring(entry):
    notify(entry.customer, "wallet_expiring", "رصيدك هينتهي قريب",
           f"{entry.remaining / 100:g} جنيه في محفظتك هينتهوا يوم {entry.expires_at.astimezone(CAIRO):%d/%m}. استخدمهم في غسلتك الجاية.",
           {"wallet_entry": entry.id}, dedupe_key=f"wallet-expiring:{entry.id}")


def next_wash(customer, last_order):
    notify(customer, "next_wash", "وقت الغسلة الجاية", "عربيتك محتاجة غسلة؟ احجز في دقيقة.",
           {"action": "book"}, dedupe_key=f"next-wash:{last_order.id}")


def car_model_to_review(car):
    notify_managers("car_model_to_review", "موديل عربية جديد محتاج مراجعة",
                    f"عميل كتب موديل «{car.unlisted_model_name}» ({car.brand.name_en}). راجعه وضيفه.", {"car": car.id})


def area_now_covered(request, zone):
    notify(request.customer, "area_now_covered", "وصلنا عندك!", f"بقينا بنخدم {zone.name}. احجز أول غسلة.",
           {"action": "book"})


def bad_rating(rating):
    call = " والعميل طالب «كلمني»." if rating.call_requested else ""
    notify_managers("bad_rating", f"تقييم وحش ({rating.stars} نجوم)",
                    f"طلب {rating.order_id}، الفني {rating.technician.full_name}.{call}",
                    {"order": rating.order_id, "rating": rating.id})


def damage_report(report):
    notify_managers("damage_report", "بلاغ ضرر", f"طلب {report.order_id}: {report.description[:200]}",
                    {"order": report.order_id, "damage_report": report.id})


def wash_card_one_left(customer, percent, order):
    notify(customer, "wash_card", "فاضلك طلب واحد",
           f"اطلب مرة كمان، والطلب اللي بعده عليه خصم {percent}% من كارت الغسيل.",
           {"action": "book"}, dedupe_key=f"wash-card-one-left:{order.id}")


def wash_card_ready(customer, percent, order):
    text = "ببلاش" if percent >= 100 else f"عليه خصم {percent}%"
    notify(customer, "wash_card", "طلبك الجاي " + text,
           f"كمّلت كارت الغسيل. طلبك الجاي {text} على الخدمات.",
           {"action": "book"}, dedupe_key=f"wash-card-ready:{order.id}")


def winback(customer, last_order):
    notify(customer, "winback", "وحشتنا", "بقالك فترة مغسلتش عربيتك معانا. احجز غسلتك الجاية في دقيقة.",
           {"action": "book"}, dedupe_key=f"winback:{last_order.id}")


def subscription_confirmed(period):
    sub = period.subscription
    notify(sub.customer, "subscription", "اشتراكك اتأكد",
           f"اشتراك «{sub.plan.name}» من {period.start_date:%d/%m} لحد {period.end_date:%d/%m}. "
           f"مواعيدك في «طلباتي».", {"subscription": sub.id})


def subscription_renewal(period):
    sub = period.subscription
    notify(sub.customer, "subscription", "اشتراكك قرب يخلص",
           f"اشتراك «{sub.plan.name}» بيخلص يوم {period.end_date:%d/%m}. جدده عشان تحافظ على ميعادك.",
           {"subscription": sub.id, "action": "renew"}, dedupe_key=f"subscription-renewal:{period.id}")
