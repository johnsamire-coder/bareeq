from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsCustomer, IsManager
from core.errors import BusinessError
from scheduling.availability import local_day_bounds

from .booking import available_slots, confirm_order, create_order, reassign
from .models import Order
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


class MyOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
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
        order = create_order(request.user, d["address"], d["items"], d["start"])
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        s = ConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order = confirm_order(self.get_object(), s.validated_data["payment_method"])
        return Response(OrderSerializer(order).data)


class ManagerOrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET ?date=YYYY-MM-DD&technician=&zone=. POST {id}/reassign/ {technician, force}."""

    permission_classes = [IsManager]
    serializer_class = ManagerOrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related("technician", "zone", "customer").prefetch_related("items")
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
        order = reassign(self.get_object(), tech, force=s.validated_data["force"])
        return Response(ManagerOrderSerializer(order).data)
