"""Manager: customers list and one customer's file."""
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import CustomerNote, User
from accounts.permissions import IsManager
from core.errors import BusinessError
from feedback.models import Rating
from orders.models import CustomerCharge, Order
from payments import wallet
from payments.models import Invoice, WalletEntry


@api_view(["GET"])
@permission_classes([IsManager])
def customers(request):
    """GET ?search= (name or phone). Newest first, 100 at most."""
    q = (request.query_params.get("search") or "").strip()
    qs = User.objects.filter(role=User.Role.CUSTOMER)
    if q:
        digits = q.lstrip("0")
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=digits or q))
    qs = qs.annotate(
        completed=Count("orders", filter=Q(orders__status=Order.Status.COMPLETED)),
        last_order=Max("orders__scheduled_start", filter=Q(orders__status=Order.Status.COMPLETED)),
    ).order_by("-date_joined")[:100]
    paid = dict(Invoice.objects.filter(status="issued", order__customer__in=list(qs)).values("order__customer")
                .annotate(s=Sum("total")).values_list("order__customer", "s"))
    return Response([{
        "id": u.id, "name": u.full_name, "phone": u.phone, "date_joined": u.date_joined, "is_active": u.is_active,
        "completed_orders": u.completed, "last_order": u.last_order, "total_paid": paid.get(u.id, 0),
    } for u in qs])


def _profile(u):
    from orders.serializers import ManagerOrderSerializer
    from payments.serializers import WalletEntrySerializer

    orders = Order.objects.filter(customer=u).select_related("zone", "technician").prefetch_related("items")[:50]
    return {
        "id": u.id, "name": u.full_name, "phone": u.phone, "date_joined": u.date_joined, "is_active": u.is_active,
        "device": u.get_signup_device_type_display(), "heard_about": u.heard_about.label if u.heard_about else None,
        "referral_code_entered": u.referral_code_entered,
        "stats": {
            "completed_orders": Order.objects.filter(customer=u, status=Order.Status.COMPLETED).count(),
            "cancelled_orders": Order.objects.filter(customer=u, status__in=[
                Order.Status.CANCELLED_BY_CUSTOMER, Order.Status.CAR_NOT_FOUND]).count(),
            "total_paid": Invoice.objects.filter(status="issued", order__customer=u).aggregate(s=Sum("total"))["s"] or 0,
        },
        "wallet_balance": wallet.balance(u),
        "wallet_entries": WalletEntrySerializer(WalletEntry.objects.filter(customer=u).order_by("-created_at")[:30], many=True).data,
        "charges": [{"id": c.id, "label": c.get_kind_display(), "amount": c.amount, "created_at": c.created_at,
                     "waived": c.waived_at is not None, "waive_reason": c.waive_reason,
                     "paid": bool(c.applied_to_order_id and c.applied_to_order.status == Order.Status.COMPLETED)}
                    for c in CustomerCharge.objects.filter(customer=u).select_related("applied_to_order")],
        "ratings": [{"order": r.order_id, "stars": r.stars, "comment": r.comment, "created_at": r.created_at}
                    for r in Rating.objects.filter(customer=u)[:20]],
        "notes": [{"id": n.id, "text": n.text, "by": n.created_by.full_name, "created_at": n.created_at}
                  for n in CustomerNote.objects.filter(customer=u).select_related("created_by")],
        "orders": ManagerOrderSerializer(orders, many=True).data,
    }


@api_view(["GET"])
@permission_classes([IsManager])
def customer_profile(request, pk):
    return Response(_profile(get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER)))


@api_view(["POST"])
@permission_classes([IsManager])
def customer_note(request, pk):
    u = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER)
    text = (request.data.get("text") or "").strip()
    if not text:
        raise BusinessError("note_required", "اكتب الملاحظة.")
    CustomerNote.objects.create(customer=u, text=text[:1000], created_by=request.user)
    return Response(_profile(u), status=201)
