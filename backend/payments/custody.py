"""Technician custody (عهدة): the running account of cash differences per technician."""
from django.db import transaction
from django.db.models import Q, Sum

from accounts.models import User
from core.errors import BusinessError

from .models import TechnicianCustody

K = TechnicianCustody.Kind


def _totals(qs):
    t = qs.aggregate(
        shortages=Sum("amount", filter=Q(kind=K.SHORTAGE), default=0),
        overages=Sum("amount", filter=Q(kind=K.OVERAGE), default=0),
        settled=Sum("amount", filter=Q(kind=K.SETTLEMENT), default=0),
    )
    t["balance"] = t["shortages"] - t["overages"] - t["settled"]
    return t


def custody_balance(technician):
    """What the technician owes now (negative = the business owes him)."""
    return _totals(TechnicianCustody.objects.filter(technician=technician))["balance"]


def custody_report():
    """One row per technician: total shortages, overages, settlements and the balance."""
    rows = []
    for tech in User.objects.filter(role=User.Role.TECHNICIAN).order_by("full_name", "id"):
        qs = TechnicianCustody.objects.filter(technician=tech)
        t = _totals(qs)
        last = qs.first()
        rows.append({"technician": tech.id, "technician_name": tech.full_name, "is_active": tech.is_active,
                     "entries_count": qs.count(), "last_at": last.created_at if last else None, **t})
    rows.sort(key=lambda r: -r["balance"])
    return rows


@transaction.atomic
def settle_custody(technician, amount, manager, reason):
    """The manager records that the technician paid back (or it was deducted)."""
    reason = (reason or "").strip()
    if not reason:
        raise BusinessError("reason_required", "اكتب السبب (دفعها كاش؟ اتخصمت من المرتب؟).")
    if amount <= 0:
        raise BusinessError("bad_amount", "المبلغ لازم يكون أكبر من صفر.")
    # Lock this technician's rows so two settlements can't both pass the check.
    list(TechnicianCustody.objects.select_for_update().filter(technician=technician))
    balance = custody_balance(technician)
    if amount > balance:
        raise BusinessError("more_than_balance", "المبلغ أكبر من العهدة اللي على الفني.")
    return TechnicianCustody.objects.create(technician=technician, kind=K.SETTLEMENT, amount=amount,
                                            note=reason, created_by=manager)
