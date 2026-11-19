from datetime import date

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsCustomer, IsManager, IsTechnician
from core.errors import BusinessError
from core.services import get_setting
from orders.models import Order
from orders.serializers import ManagerOrderSerializer
from scheduling.availability import CAIRO

from . import wallet
from .closing import closing_summary, confirm_closing, record_materials, submit_closing
from .custody import custody_balance, custody_report, settle_custody
from .invoices import cancel_invoice
from .models import DailyClosing, Invoice, Material, Payment, TechnicianCustody, WalletEntry
from .payments import mark_refunded, review_instapay
from .serializers import (
    DailyClosingSerializer,
    InvoiceSerializer,
    ManualCreditSerializer,
    MaterialSerializer,
    MaterialsSerializer,
    PaymentSerializer,
    ReasonSerializer,
    SettleCustodySerializer,
    SubmitClosingSerializer,
    TechnicianCustodySerializer,
    WalletEntrySerializer,
)


# ---------- customer ----------

@api_view(["GET"])
@permission_classes([AllowAny])
def payment_info(request):
    """What the payment screen shows: InstaPay details, wallet balance and the % limit."""
    data = {"instapay_details": get_setting("instapay-payment-details"),
            "card_payment_enabled": bool(get_setting("card-payment-enabled")),
            "wallet_max_order_share_percent": get_setting("wallet-max-order-share-percent"),
            # Shown before the customer cancels or reschedules (same numbers as the terms).
            "cancellation_free_until_hours": get_setting("cancellation-free-until-hours"),
            "cancellation_late_fee": get_setting("cancellation-late-fee")}
    if request.user.is_authenticated and request.user.role == "customer":
        data["wallet_balance"] = wallet.balance(request.user)
    return Response(data)


@api_view(["GET"])
@permission_classes([IsCustomer])
def my_wallet(request):
    entries = WalletEntry.objects.filter(customer=request.user).order_by("-created_at", "-id")
    return Response({"balance": wallet.balance(request.user),
                     "entries": WalletEntrySerializer(entries, many=True).data})


@api_view(["GET"])
@permission_classes([IsCustomer])
def my_invoices(request):
    qs = Invoice.objects.filter(order__customer=request.user)
    return Response(InvoiceSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def proof_file(request, pk):
    p = get_object_or_404(Payment.objects.select_related("order"), pk=pk)
    if not p.proof or not (request.user.role == "manager" or request.user.id == p.order.customer_id):
        return Response({"code": "forbidden", "detail": "مش مسموح."}, status=403)
    return FileResponse(p.proof.open("rb"), content_type="image/jpeg")


# ---------- technician ----------

@api_view(["GET"])
@permission_classes([IsTechnician])
def technician_materials(request):
    return Response(MaterialSerializer(Material.objects.filter(is_active=True), many=True).data)


@api_view(["POST"])
@permission_classes([IsTechnician])
def technician_job_materials(request, pk):
    order = get_object_or_404(Order, pk=pk, technician=request.user)
    s = MaterialsSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    order = record_materials(order, request.user, s.validated_data["items"])
    return Response({"order": order.id, "materials_cost": order.materials_cost})


@api_view(["GET", "POST"])
@permission_classes([IsTechnician])
def technician_closing(request):
    """GET ?date= : today's cash and materials. POST {date, cash_handed, note}: hand over the cash."""
    if request.method == "GET":
        raw = request.query_params.get("date")
        try:
            day = date.fromisoformat(raw) if raw else timezone.now().astimezone(CAIRO).date()
        except ValueError:
            raise BusinessError("bad_date", "التاريخ مش صحيح.")
        return Response({**closing_summary(request.user, day), "custody_balance": custody_balance(request.user)})
    s = SubmitClosingSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    return Response(DailyClosingSerializer(submit_closing(request.user, d["date"], d["cash_handed"], d["note"])).data)


# ---------- manager ----------

class ManagerPaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET ?status=pending_review (InstaPay to check) or ?status=refund_due."""

    permission_classes = [IsManager]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = Payment.objects.select_related("order__customer")
        for f in ("status", "method", "order"):
            if self.request.query_params.get(f):
                qs = qs.filter(**{f: self.request.query_params[f]})
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return Response(PaymentSerializer(review_instapay(self.get_object(), request.user, approve=True)).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        s = ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        p = review_instapay(self.get_object(), request.user, approve=False, reason=s.validated_data["reason"])
        return Response(PaymentSerializer(p).data)

    @action(detail=True, methods=["post"])
    def refunded(self, request, pk=None):
        return Response(PaymentSerializer(mark_refunded(self.get_object(), request.user)).data)


class ManagerInvoiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsManager]
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        s = ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(InvoiceSerializer(cancel_invoice(self.get_object(), request.user,
                                                         s.validated_data["reason"])).data)


class ManagerClosingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET ?status=submitted&date=. Differences show in 'difference' (negative = short)."""

    permission_classes = [IsManager]
    serializer_class = DailyClosingSerializer

    def get_queryset(self):
        qs = DailyClosing.objects.select_related("technician")
        for f in ("status", "date", "technician"):
            if self.request.query_params.get(f):
                qs = qs.filter(**{f: self.request.query_params[f]})
        return qs

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        s = ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        closing = confirm_closing(self.get_object(), request.user, s.validated_data["reason"])
        return Response(DailyClosingSerializer(closing).data)


class ManagerMaterialViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManager]
    serializer_class = MaterialSerializer
    queryset = Material.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]


@api_view(["GET"])
@permission_classes([IsManager])
def manager_customer_wallet(request, customer_id):
    customer = get_object_or_404(User, pk=customer_id, role="customer")
    entries = WalletEntry.objects.filter(customer=customer).order_by("-created_at", "-id")
    return Response({"balance": wallet.balance(customer), "entries": WalletEntrySerializer(entries, many=True).data})


@api_view(["POST"])
@permission_classes([IsManager])
def manager_wallet_credit(request):
    s = ManualCreditSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    customer = get_object_or_404(User, pk=s.validated_data["customer"], role="customer")
    e = wallet.credit(customer, s.validated_data["amount"], WalletEntry.Kind.MANUAL, created_by=request.user,
                      note=s.validated_data["note"])
    return Response(WalletEntrySerializer(e).data, status=201)


@api_view(["GET"])
@permission_classes([IsManager])
def manager_order_money(request, pk):
    """Money view of one order: revenue next to what was really collected (the
    difference is the wallet), oil, materials and «هامش الغسلة»."""
    o = get_object_or_404(Order, pk=pk)
    return Response({**ManagerOrderSerializer(o).data, "oil_total": o.oil_total,
                     "materials_cost": o.materials_cost, "wash_margin": o.wash_margin,
                     "materials": [{"material": u.material.name, "quantity": str(u.quantity), "cost": u.cost}
                                   for u in o.material_usages.select_related("material")]})


# ---------- technician custody (عهدة) ----------

@api_view(["GET"])
@permission_classes([IsManager])
def manager_custody(request):
    """All technicians with their custody totals, or ?technician=ID for one with its lines."""
    tech_id = request.query_params.get("technician")
    if not tech_id:
        return Response(custody_report())
    tech = get_object_or_404(User, pk=tech_id, role=User.Role.TECHNICIAN)
    row = next(r for r in custody_report() if r["technician"] == tech.id)
    entries = TechnicianCustody.objects.filter(technician=tech).select_related("closing", "created_by")
    return Response({**row, "entries": TechnicianCustodySerializer(entries, many=True).data})


@api_view(["POST"])
@permission_classes([IsManager])
def manager_custody_settle(request):
    s = SettleCustodySerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    tech = get_object_or_404(User, pk=d["technician"], role=User.Role.TECHNICIAN)
    row = settle_custody(tech, d["amount"], request.user, d["reason"])
    return Response(TechnicianCustodySerializer(row).data, status=201)
