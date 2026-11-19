from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsManagerOrSupervisor, limit_to_zones, zone_ids_of, IsCustomer, IsManager
from core.errors import BusinessError
from scheduling.availability import local_day_bounds

from .booking import available_slots, confirm_order, create_order, reassign
from .models import Order
from .views_lifecycle import CustomerOrderActionsMixin
from .serializers import (
    ConfirmSerializer,
    CreateOrderSerializer,
    ManagerOrderSerializer,
    OrderSerializer,
    ReassignSerializer,
    SlotsRequestSerializer,
)


@api_view(["POST"])
@permission_classes([IsCustomer])
def slots(request):
    """Body: {address, items: [{car, services, oil_type?}]} -> price, minutes and free times per day."""
    s = SlotsRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    return Response(available_slots(request.user, s.validated_data["address"], s.validated_data["items"]))


class MyOrderViewSet(CustomerOrderActionsMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                     viewsets.GenericViewSet):
    """Customer's orders. POST books a time and holds it for the hold minutes."""

    permission_classes = [IsCustomer]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return (Order.objects.filter(customer=self.request.user)
                .select_related("technician", "zone").prefetch_related("items__car__brand", "items__car__model"))

    def create(self, request, *args, **kwargs):
        s = CreateOrderSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        order = create_order(request.user, d["address"], d["items"], d["start"], express=d["express"])
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], parser_classes=[JSONParser, MultiPartParser, FormParser])
    def confirm(self, request, pk=None):
        """{payment_method: cash|instapay, wallet_amount (piastres, optional), proof (image, InstaPay)}."""
        s = ConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        order = confirm_order(self.get_object(), d["payment_method"], wallet_amount=d.get("wallet_amount") or 0,
                              proof_file=d.get("proof"))
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["get"])
    def invoice(self, request, pk=None):
        from payments.models import Invoice
        from payments.serializers import InvoiceSerializer

        inv = Invoice.objects.filter(order=self.get_object()).order_by("-issued_at").first()
        if inv is None:
            raise BusinessError("no_invoice", "الفاتورة بتطلع بعد ما الشغل يخلص.", status=404)
        return Response(InvoiceSerializer(inv).data)


class ManagerOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET ?date=YYYY-MM-DD&technician=&zone=. POST {id}/reassign/ {technician, force}."""

    permission_classes = [IsManagerOrSupervisor]
    serializer_class = ManagerOrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related("technician", "zone", "customer").prefetch_related("items")
        qs = limit_to_zones(qs, self.request.user)
        p = self.request.query_params
        if p.get("date"):
            try:
                start, end = local_day_bounds(date.fromisoformat(p["date"]))
            except ValueError:
                raise BusinessError("bad_date", "التاريخ مش صحيح.")
            qs = qs.filter(scheduled_start__gte=start, scheduled_start__lt=end)
        for f in ("technician", "zone", "status"):
            if p.get(f):
                qs = qs.filter(**{f: p[f]})
        return qs.order_by("scheduled_start")

    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        s = ReassignSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        tech = get_object_or_404(User, pk=s.validated_data["technician"])
        order = self.get_object()
        if request.user.role == User.Role.SUPERVISOR:
            if s.validated_data["force"]:
                raise BusinessError("manager_only", "النقل بالإجبار للمدير بس.", status=403)
            prof = getattr(tech, "technician_profile", None)
            if prof is None or not prof.zones.filter(id__in=zone_ids_of(request.user)).exists():
                raise BusinessError("not_your_zone", "الفني ده مش في مناطقك.", status=403)
        order = reassign(order, tech, force=s.validated_data["force"])
        return Response(ManagerOrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        if request.user.role != User.Role.MANAGER:
            raise BusinessError("manager_only", "الإلغاء للمدير بس.", status=403)
        from .lifecycle import cancel_by_company
        from .serializers import ReasonSerializer

        s = ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order = cancel_by_company(self.get_object(), request.user, s.validated_data["reason"])
        return Response(ManagerOrderSerializer(order).data)

    @action(detail=True, methods=["get"])
    def photos(self, request, pk=None):
        from .serializers import OrderPhotoSerializer

        return Response(OrderPhotoSerializer(self.get_object().photos.all(), many=True).data)
