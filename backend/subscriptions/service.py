"""Subscribing, paying, renewing, and the visits of a monthly subscription."""
import uuid
from datetime import datetime, timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from core.errors import BusinessError
from core.services import get_setting
from orders.booking import create_order
from orders.models import Order
from payments import wallet
from payments.models import Payment
from scheduling.availability import CAIRO
from services.pricing import build_quote

from .models import Subscription, SubscriptionPeriod, SubscriptionPlan

PERIOD_DAYS = 28
PS = SubscriptionPeriod.Status


# ---------- price ----------

def split(total, n):
    """Whole pounds per visit; the first visit takes the leftover."""
    each = total // n // 100 * 100
    return [total - each * (n - 1)] + [each] * (n - 1)


def visit_quote(plan, car, address):
    if address.zone is None:
        raise BusinessError("outside_service_area", "العنوان ده برا المناطق اللي بنخدمها دلوقتي.")
    return build_quote([s.id for s in plan.services.all()], address.zone, car.size_class, car.parking)


def plan_price(plan, car, address):
    """(price, normal price) for one month, whole pounds."""
    normal = visit_quote(plan, car, address)["total"] * plan.washes_per_month
    price = normal * (100 - plan.discount_percent) // 100 // 100 * 100
    return price, normal


def interval_days(plan):
    return max(1, PERIOD_DAYS // plan.washes_per_month)


# ---------- booking the visits of a month ----------

def _book_period(sub, number, first_start, check_first_window=True):
    plan = sub.plan
    price, normal = plan_price(plan, sub.car, sub.address)
    first_day = first_start.astimezone(CAIRO).date()
    period = SubscriptionPeriod.objects.create(subscription=sub, number=number, start_date=first_day,
                                               end_date=first_day + timedelta(days=PERIOD_DAYS - 1),
                                               price=price, normal_price=normal)
    items = [{"car": sub.car_id, "services": [s.id for s in plan.services.all()]}]
    shares = split(price, plan.washes_per_month)
    busy = []
    for i in range(plan.washes_per_month):
        start = first_start + timedelta(days=i * interval_days(plan))
        try:
            order = create_order(sub.customer, sub.address_id, items, start, prefer_technician=sub.technician,
                                 check_window=check_first_window and i == 0, attach_charges=False,
                                 subscription_period=period)
        except BusinessError as e:
            if e.detail["code"] in ("slot_taken", "day_closed"):
                busy.append(start.astimezone(CAIRO).strftime("%d/%m"))
                continue
            raise
        order.extra_discount_kind = "subscription"
        order.extra_discount = max(0, order.total - shares[i])
        order.save(update_fields=["extra_discount_kind", "extra_discount", "updated_at"])
        if sub.technician_id is None:
            sub.technician = order.technician
            sub.save(update_fields=["technician"])
    if busy:
        raise BusinessError("subscription_slots_taken",
                            f"الميعاد ده مش فاضي في الأيام دي: {'، '.join(busy)}. اختار يوم أو ساعة تانية.", status=409)
    return period


@transaction.atomic
def subscribe(customer, plan_id, car_id, address_id, first_start):
    from cars.models import CustomerCar
    from places.models import Address

    plan = SubscriptionPlan.objects.filter(pk=plan_id, is_active=True).first()
    if plan is None:
        raise BusinessError("plan_not_found", "الباقة دي مش متاحة.")
    if any(s.is_oil_change for s in plan.services.all()):
        raise BusinessError("plan_has_oil", "الباقة مينفعش يبقى فيها تغيير زيت.")
    car = CustomerCar.objects.filter(pk=car_id, customer=customer, is_active=True).first()
    address = Address.objects.filter(pk=address_id, customer=customer, is_active=True).first()
    if car is None or address is None:
        raise BusinessError("not_found", "العربية أو العنوان مش موجودين.")
    if Subscription.objects.filter(customer=customer, car=car, status=Subscription.Status.ACTIVE,
                                   periods__status__in=[PS.PAID, PS.PENDING_PAYMENT]).exists():
        raise BusinessError("already_subscribed", "العربية دي مشتركة بالفعل.")
    local = first_start.astimezone(CAIRO)
    sub = Subscription.objects.create(customer=customer, plan=plan, car=car, address=address,
                                      weekday=local.weekday(), start_time=local.time())
    _book_period(sub, 1, first_start)
    return sub


def current_period(sub):
    return sub.periods.exclude(status=PS.EXPIRED).order_by("-number").first()


@transaction.atomic
def renew(sub, customer):
    sub = Subscription.objects.select_for_update().get(pk=sub.pk)
    if sub.customer_id != customer.id:
        raise BusinessError("not_yours", "الاشتراك ده مش بتاعك.", status=403)
    last = current_period(sub)
    if sub.status != Subscription.Status.ACTIVE or last is None or last.status != PS.PAID:
        raise BusinessError("cannot_renew", "الاشتراك ده مينفعش يتجدد دلوقتي.")
    if not sub.plan.is_active:
        raise BusinessError("plan_not_found", "الباقة دي مبقتش متاحة. اختار باقة تانية.")
    next_day = last.end_date + timedelta(days=1)
    while next_day.weekday() != sub.weekday:
        next_day += timedelta(days=1)
    start = datetime.combine(next_day, sub.start_time, tzinfo=CAIRO)
    sub.renew = True
    sub.save(update_fields=["renew"])
    return _book_period(sub, last.number + 1, start, check_first_window=False)


def stop_renewal(sub, customer):
    if sub.customer_id != customer.id:
        raise BusinessError("not_yours", "الاشتراك ده مش بتاعك.", status=403)
    sub.renew = False
    sub.save(update_fields=["renew"])
    return sub


# ---------- paying a month ----------

def _lock_period(period, customer):
    period = SubscriptionPeriod.objects.select_for_update().select_related("subscription").get(pk=period.pk)
    if period.subscription.customer_id != customer.id:
        raise BusinessError("not_yours", "الاشتراك ده مش بتاعك.", status=403)
    if period.status != PS.PENDING_PAYMENT:
        raise BusinessError("not_pending", "الشهر ده مش مستني دفع.")
    visits = list(Order.objects.select_for_update().filter(subscription_period=period).order_by("scheduled_start"))
    now = timezone.now()
    if not visits or any(o.status != Order.Status.PENDING_PAYMENT or (o.hold_expires_at and o.hold_expires_at <= now)
                         for o in visits):
        raise BusinessError("hold_expired", "خلص وقت الحجز المؤقت. اشترك تاني واختار الميعاد.")
    return period, visits


def _check_wallet(period, wallet_amount, customer):
    wallet_amount = wallet.whole_pounds(int(wallet_amount or 0))
    if wallet_amount < 0 or wallet_amount > wallet.max_usable_for(period.price):
        raise BusinessError("wallet_over_limit", "مينفعش تدفع الجزء ده كله من المحفظة.")
    if wallet_amount > wallet.balance(customer):
        raise BusinessError("insufficient_wallet", "رصيد المحفظة مش كفاية.")
    return wallet_amount


def _spread(period, visits, method, money_amount, wallet_amount, status, proof_bytes=None):
    """Record the month's money on its visits (whole pounds each)."""
    shares = [o.amount_due for o in visits]
    wallet_parts = split(wallet_amount, len(visits)) if wallet_amount else [0] * len(visits)
    wallet_parts = [min(w, s) for w, s in zip(wallet_parts, shares)]
    leftover = wallet_amount - sum(wallet_parts)
    for i, o in enumerate(visits):  # put any leftover wallet on visits that can take it
        extra = min(leftover, shares[i] - wallet_parts[i])
        wallet_parts[i] += extra
        leftover -= extra
    now = timezone.now()
    name = f"sub-{period.id}-{uuid.uuid4().hex}.jpg" if proof_bytes else None
    for o, share, w in zip(visits, shares, wallet_parts):
        if w:
            wallet.spend(o.customer, w, order=o)
        p = Payment(order=o, method=method, amount=share - w, status=status,
                    reviewed_at=now if status == Payment.Status.CONFIRMED else None)
        if proof_bytes:
            p.proof.save(name, ContentFile(proof_bytes), save=False)
        if p.amount:
            p.save()
        o.status = Order.Status.CONFIRMED
        o.payment_method = method
        o.wallet_used = w
        o.hold_expires_at = None
        o.save(update_fields=["status", "payment_method", "wallet_used", "hold_expires_at", "updated_at"])
    period.status, period.paid_at = PS.PAID, now
    period.wallet_used, period.payment_method = wallet_amount, method
    period.save()
    from notifications import events

    events.subscription_confirmed(period)


@transaction.atomic
def pay_instapay(period, customer, proof_file, wallet_amount=0):
    from orders.photos import shrink

    if proof_file is None:
        raise BusinessError("proof_required", "ارفع صورة التحويل.")
    period, visits = _lock_period(period, customer)
    wallet_amount = _check_wallet(period, wallet_amount, customer)
    jpeg, _ = shrink(proof_file.read())
    _spread(period, visits, Payment.Method.INSTAPAY, period.price - wallet_amount, wallet_amount,
            Payment.Status.PENDING_REVIEW, proof_bytes=jpeg)
    from notifications import events

    events.instapay_to_review(visits[0])
    return period


@transaction.atomic
def start_online(period, customer, wallet_amount=0):
    from payments.gateway import get_gateway
    from payments.models import OnlinePayment

    if not get_setting("card-payment-enabled"):
        raise BusinessError("payment_method_not_available", "الدفع بالكارت مش متاح دلوقتي.")
    period, visits = _lock_period(period, customer)
    wallet_amount = _check_wallet(period, wallet_amount, customer)
    gw = get_gateway()
    p = OnlinePayment.objects.create(ref=uuid.uuid4().hex, order=visits[0], period=period, provider=gw.name,
                                     amount=period.price - wallet_amount, wallet_amount=wallet_amount)
    extra = timedelta(minutes=get_setting("card-payment-hold-extra-minutes"))
    now = timezone.now()
    for o in visits:
        o.hold_expires_at = max(o.hold_expires_at or now, now) + extra
        o.save(update_fields=["hold_expires_at", "updated_at"])
    return p


def online_paid(online_payment):
    """Called by payments/online.py when the company confirms a subscription payment.
    Returns False when the month cannot be confirmed any more (money to give back)."""
    period = SubscriptionPeriod.objects.select_for_update().get(pk=online_payment.period_id)
    visits = list(Order.objects.select_for_update().filter(subscription_period=period).order_by("scheduled_start"))
    if period.status != PS.PENDING_PAYMENT or any(o.status != Order.Status.PENDING_PAYMENT for o in visits):
        return False
    if online_payment.wallet_amount > wallet.balance(period.subscription.customer):
        return False
    _spread(period, visits, Payment.Method.CARD, online_payment.amount, online_payment.wallet_amount,
            Payment.Status.CONFIRMED)
    return True


# ---------- visits ----------

def check_reschedule(order, new_start):
    """A subscription visit moves only inside its month."""
    period = order.subscription_period
    day = new_start.astimezone(CAIRO).date()
    if not (period.start_date <= day <= period.end_date):
        raise BusinessError("outside_subscription_month",
                            f"زيارة الاشتراك تتأجل جوه نفس الشهر بس (لحد {period.end_date:%d/%m}).")


def on_company_cancel(order):
    """The company cancelled a paid visit (weather, ...): the customer books another one."""
    period = SubscriptionPeriod.objects.select_for_update().get(pk=order.subscription_period_id)
    if period.status == PS.PAID:
        period.makeup_visits += 1
        period.save(update_fields=["makeup_visits"])


@transaction.atomic
def book_makeup(period, customer, start):
    period = SubscriptionPeriod.objects.select_for_update().select_related("subscription").get(pk=period.pk)
    sub = period.subscription
    if sub.customer_id != customer.id:
        raise BusinessError("not_yours", "الاشتراك ده مش بتاعك.", status=403)
    if period.makeup_visits <= 0:
        raise BusinessError("no_makeup", "مفيش زيارة تتعوض.")
    last_day = period.end_date + timedelta(days=get_setting("subscription-makeup-extra-days"))
    if not (timezone.now() < start and start.astimezone(CAIRO).date() <= last_day):
        raise BusinessError("outside_subscription_month", f"اختار ميعاد لحد {last_day:%d/%m}.")
    items = [{"car": sub.car_id, "services": [s.id for s in sub.plan.services.all()]}]
    order = create_order(customer, sub.address_id, items, start, prefer_technician=sub.technician,
                         check_window=False, attach_charges=False, subscription_period=period)
    # Already paid with the month.
    order.extra_discount_kind, order.extra_discount = "subscription", order.total
    order.status, order.payment_method, order.hold_expires_at = Order.Status.CONFIRMED, "subscription", None
    order.save()
    period.makeup_visits -= 1
    period.save(update_fields=["makeup_visits"])
    return order


def expire_unpaid():
    """Months whose visits' holds ran out (run_scheduled_jobs)."""
    n = 0
    for period in SubscriptionPeriod.objects.filter(status=PS.PENDING_PAYMENT):
        if not period.visits.filter(status=Order.Status.PENDING_PAYMENT).exists():
            period.status = PS.EXPIRED
            period.save(update_fields=["status"])
            n += 1
    return n


def renewal_reminders():
    from notifications import events

    now = timezone.now()
    horizon = now.astimezone(CAIRO).date() + timedelta(days=get_setting("subscription-renewal-reminder-days"))
    n = 0
    for period in SubscriptionPeriod.objects.select_related("subscription").filter(
            status=PS.PAID, end_date__lte=horizon, renewal_reminded_at__isnull=True,
            subscription__status=Subscription.Status.ACTIVE, subscription__renew=True):
        if period.subscription.periods.filter(number__gt=period.number).exclude(status=PS.EXPIRED).exists():
            continue
        events.subscription_renewal(period)
        period.renewal_reminded_at = now
        period.save(update_fields=["renewal_reminded_at"])
        n += 1
    return n


def end_finished():
    """Subscriptions whose last paid month is over and not renewed."""
    today = timezone.now().astimezone(CAIRO).date()
    n = 0
    for sub in Subscription.objects.filter(status=Subscription.Status.ACTIVE):
        last = current_period(sub)
        if last is None or (last.status == PS.PAID and last.end_date < today):
            sub.status = Subscription.Status.ENDED
            sub.save(update_fields=["status"])
            n += 1
    return n
