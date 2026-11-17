from datetime import date

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsManager, IsTechnician
from core.errors import BusinessError
from scheduling.availability import CAIRO, local_day_bounds

from . import lifecycle
from .charges import outstanding_charges, waive_charge
from .models import CustomerCharge, Order, OrderPhoto
from .photos import add_photo
from .serializers import (
    CustomerChargeSerializer,
    ManagerOrderSerializer,
    OrderPhotoSerializer,
    OrderSerializer,
    PhotoUploadSerializer,
    PointSerializer,
    ReasonSerializer,
    RescheduleSerializer,
)


class TechnicianJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """The technician's jobs. GET ?date=YYYY-MM-DD (default today), in time order."""

    permission_classes = [IsTechnician]
    serializer_class = ManagerOrderSerializer  # he needs the customer's name, phone and pin

    def get_queryset(self):
        qs = Order.objects.filter(technician=self.request.user).exclude(status__in=Order.FREE_STATUSES)
        if self.action == "list":
            raw = self.request.query_params.get("date")
            try:
                day = date.fromisoformat(raw) if raw else timezone.now().astimezone(CAIRO).date()
            except ValueError:
                raise BusinessError("bad_date", "التاريخ مش صحيح.")
            start, end = local_day_bounds(day)
            qs = qs.filter(scheduled_start__gte=start, scheduled_start__lt=end)
        return qs.select_related("customer", "zone").prefetch_related("items__car").order_by("scheduled_start")

    def _step(self, request, fn):
        p = PointSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        order = fn(self.get_object(), request.user, **p.validated_data)
        return Response(ManagerOrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="on-the-way")
    def on_the_way(self, request, pk=None):
        return self._step(request, lifecycle.on_the_way)

    @action(detail=True, methods=["post"])
    def arrived(self, request, pk=None):
        return self._step(request, lifecycle.arrived)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._step(request, lifecycle.start_job)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Body: {cash_collected (piastres, when money is due), lat, lng}."""
        p = PointSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        raw = request.data.get("cash_collected")
        try:
            cash = None if raw in (None, "") else int(raw)
        except (TypeError, ValueError):
            raise BusinessError("bad_amount", "المبلغ مش صحيح.")
        order = lifecycle.complete_job(self.get_object(), request.user, cash_collected=cash, **p.validated_data)
        return Response(ManagerOrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="called-customer")
    def called_customer(self, request, pk=None):
        return Response(ManagerOrderSerializer(lifecycle.called_customer(self.get_object(), request.user)).data)

    @action(detail=True, methods=["post"], url_path="car-not-found")
    def car_not_found(self, request, pk=None):
        p = PointSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        order = lifecycle.car_not_found(self.get_object(), request.user, p.validated_data.get("lat"),
                                        p.validated_data.get("lng"))
        return Response(ManagerOrderSerializer(order).data)

    @action(detail=True, methods=["get", "post"], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        order = self.get_object()
        if request.method == "GET":
            return Response(OrderPhotoSerializer(order.photos.all(), many=True).data)
        s = PhotoUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        photo = add_photo(order, request.user, d["stage"], d["side"], d["image"].read(), d["captured_at"],
                          d["lat"], d["lng"], d.get("accuracy_m"))
        return Response(OrderPhotoSerializer(photo).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def photo_file(request, pk):
    """The photo itself. Only the order's customer, its technician, or a manager."""
    photo = get_object_or_404(OrderPhoto.objects.select_related("order"), pk=pk)
    u = request.user
    if not (u.role == "manager" or u.id in (photo.order.customer_id, photo.order.technician_id)):
        return Response({"code": "forbidden", "detail": "مش مسموح."}, status=403)
    return FileResponse(photo.image.open("rb"), content_type="image/jpeg")


class CustomerOrderActionsMixin:
    """Added to the customer's /api/orders/ endpoints."""

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        s = ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(OrderSerializer(lifecycle.cancel_by_customer(self.get_object(), s.validated_data["reason"])).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        s = RescheduleSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(OrderSerializer(lifecycle.reschedule(self.get_object(), s.validated_data["start"])).data)

    @action(detail=True, methods=["get"], url_path="photos")
    def order_photos(self, request, pk=None):
        return Response(OrderPhotoSerializer(self.get_object().photos.all(), many=True).data)


@api_view(["GET"])
@permission_classes([IsCustomer])
def my_charges(request):
    return Response(CustomerChargeSerializer(outstanding_charges(request.user), many=True).data)


class ManagerChargeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """All fees. GET ?open=1 for unpaid and not waived. POST {id}/waive/ {reason}."""

    permission_classes = [IsManager]
    serializer_class = CustomerChargeSerializer

    def get_queryset(self):
        qs = CustomerCharge.objects.select_related("customer")
        if self.request.query_params.get("open"):
            qs = qs.filter(waived_at__isnull=True).exclude(applied_to_order__status=Order.Status.COMPLETED)
        return qs

    @action(detail=True, methods=["post"])
    def waive(self, request, pk=None):
        s = ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(CustomerChargeSerializer(waive_charge(self.get_object(), request.user,
                                                              s.validated_data["reason"])).data)
