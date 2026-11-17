"""Price and duration of a set of services for one car in one zone.

All money is integer piastres. Rules (all editable by the manager):
1. A service can replace others (exterior detailing replaces exterior wash):
   the replaced one is removed with a short message.
2. "Needs shade" services on a street-parked car: warning, or refused if the
   setting services-block-needs-shade-on-street is on.
3. Bundles: if every service of a bundle is selected, its % discount applies
   to those services. Only the single best bundle applies.
4. Oil (for oil change) is a separate line, never discounted.
"""
from core.errors import BusinessError
from core.services import get_setting

from .models import Bundle, OilType, Service, ServiceDuration, ServicePrice


def percent_of(amount, percent):
    """Whole piastres, half rounded up."""
    return (amount * percent + 50) // 100


def build_quote(service_ids, zone, size_class, parking=None, oil_type_id=None):
    ids = list(dict.fromkeys(int(i) for i in service_ids))
    if not ids:
        raise BusinessError("no_services", "اختار خدمة واحدة على الأقل.")
    services = {s.id: s for s in Service.objects.filter(id__in=ids, is_active=True).prefetch_related("replaces")}
    if len(services) != len(ids):
        raise BusinessError("unknown_service", "فيه خدمة مش موجودة أو مش متاحة.")

    # 1. Replacements
    selected = dict(services)
    removed, messages = [], []
    for s in services.values():
        for r in s.replaces.all():
            if r.id in selected and s.id in selected:
                del selected[r.id]
                removed.append(r.id)
                messages.append(f"«{s.name}» بتشمل «{r.name}»، فشلنا «{r.name}».")

    # 2. Shade
    warnings = []
    if parking == "street":
        shade = [s for s in selected.values() if s.needs_shade]
        if shade:
            names = "، ".join(s.name for s in shade)
            if get_setting("services-block-needs-shade-on-street"):
                raise BusinessError("needs_shade", f"«{names}» محتاجة العربية تكون في ضل، ومينفعش في الشارع.")
            warnings.append(f"«{names}» محتاجة العربية تكون في ضل. لو تقدر تركنها في ضل وقت الخدمة يبقى أحسن.")

    # Prices and durations
    prices = {
        p.service_id: p
        for p in ServicePrice.objects.filter(service_id__in=selected, zone=zone, size_class=size_class)
    }
    minutes = {
        d.service_id: d.minutes
        for d in ServiceDuration.objects.filter(service_id__in=selected, size_class=size_class)
    }
    ordered = sorted(selected.values(), key=lambda s: (s.sort_order, s.id))
    for s in ordered:
        if s.id not in prices or s.id not in minutes:
            raise BusinessError("not_available", f"«{s.name}» مش متاحة دلوقتي في منطقتك لحجم عربيتك.")
    lines = [
        {"service": s.id, "code": s.code, "name": s.name, "price": prices[s.id].price, "minutes": minutes[s.id]}
        for s in ordered
    ]
    subtotal = sum(line["price"] for line in lines)

    # 3. Best bundle
    best, discount = None, 0
    for b in Bundle.objects.filter(is_active=True).prefetch_related("services"):
        b_ids = {s.id for s in b.services.all()}
        if b_ids and b_ids <= set(selected):
            d = percent_of(sum(prices[i].price for i in b_ids), b.discount_percent)
            if d > discount:
                best, discount = b, d

    # 4. Oil
    oil = None
    has_oil_service = any(s.is_oil_change for s in selected.values())
    if oil_type_id is not None:
        if not has_oil_service:
            raise BusinessError("oil_without_service", "نوع الزيت بيتختار مع خدمة تغيير الزيت بس.")
        o = OilType.objects.filter(id=oil_type_id, is_active=True).first()
        if o is None:
            raise BusinessError("unknown_oil", "نوع الزيت ده مش متاح.")
        oil = {"id": o.id, "name": o.name, "price": o.price}

    return {
        "lines": lines,
        "removed_services": removed,
        "messages": messages,
        "warnings": warnings,
        "subtotal": subtotal,
        "bundle": {"id": best.id, "name": best.name, "discount_percent": best.discount_percent} if best else None,
        "discount": discount,
        "oil": oil,
        "needs_oil_choice": has_oil_service and oil is None,
        "total": subtotal - discount + (oil["price"] if oil else 0),
        "total_minutes": sum(line["minutes"] for line in lines),
        "has_provisional_prices": any(prices[s.id].is_provisional for s in ordered),
    }
