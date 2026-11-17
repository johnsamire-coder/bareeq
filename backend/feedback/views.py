from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsManager
from core.errors import BusinessError
from core.services import get_setting
from orders.models import Order
from scheduling.models import ClosedDay

from .models import DamagePhoto, DamageReport, Rating, RatingTag
from .serializers import (
    ClosedDaySerializer,
    DamageReportSerializer,
    NoteSerializer,
    RatingInputSerializer,
    RatingSerializer,
    RatingTagSerializer,
)
from .service import (
    add_damage_photo,
    add_rating,
    add_rating_photo,
    close_day,
    handle_rating,
    ratings_summary,
    report_damage,
    resolve_damage,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rating_tags(request):
    return Response(RatingTagSerializer(RatingTag.objects.filter(is_active=True), many=True).data)


@api_view(["POST"])
@permission_classes([IsCustomer])
def rate_order(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    s = RatingInputSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    r, extra = add_rating(order, request.user, d["stars"], d["tags"], d["comment"], d["call_requested"])
    return Response({"rating": RatingSerializer(r).data, **extra}, status=201)


def _file(request):
    f = request.FILES.get("image")
    if f is None:
        raise BusinessError("image_required", "اختار صورة.")
    return f.read()


@api_view(["POST"])
@permission_classes([IsCustomer])
@parser_classes([MultiPartParser, FormParser])
def rating_photo(request, pk):
    rating = get_object_or_404(Rating, pk=pk, customer=request.user)
    p = add_rating_photo(rating, request.user, _file(request))
    return Response({"id": p.id}, status=201)


@api_view(["POST"])
@permission_classes([IsCustomer])
def damage_report(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    report = report_damage(order, request.user, request.data.get("description", ""))
    return Response(DamageReportSerializer(report).data, status=201)


@api_view(["POST"])
@permission_classes([IsCustomer])
@parser_classes([MultiPartParser, FormParser])
def damage_photo(request, pk):
    report = get_object_or_404(DamageReport, pk=pk, customer=request.user)
    p = add_damage_photo(report, request.user, _file(request))
    return Response({"id": p.id}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def damage_photo_file(request, pk):
    p = get_object_or_404(DamagePhoto.objects.select_related("report"), pk=pk)
    if not (request.user.role == "manager" or request.user.id == p.report.customer_id):
        return Response({"code": "forbidden", "detail": "مش مسموح."}, status=403)
    return FileResponse(p.image.open("rb"), content_type="image/jpeg")


class ManagerRatingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET ?bad=1&unhandled=1&technician=&zone=. POST {id}/handle/ {note}. GET summary/."""

    permission_classes = [IsManager]
    serializer_class = RatingSerializer

    def get_queryset(self):
        p = self.request.query_params
        qs = Rating.objects.select_related("technician", "customer", "zone").prefetch_related("tags")
        if p.get("bad"):
            qs = qs.filter(stars__lte=get_setting("ratings-bad-max-stars"))
        if p.get("unhandled"):
            qs = qs.filter(handled_at__isnull=True)
        for f in ("technician", "zone"):
            if p.get(f):
                qs = qs.filter(**{f: p[f]})
        return qs

    @action(detail=True, methods=["post"])
    def handle(self, request, pk=None):
        s = NoteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(RatingSerializer(handle_rating(self.get_object(), request.user, s.validated_data["note"])).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(ratings_summary())


class ManagerRatingTagViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManager]
    serializer_class = RatingTagSerializer
    queryset = RatingTag.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]


class ManagerDamageViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsManager]
    serializer_class = DamageReportSerializer

    def get_queryset(self):
        qs = DamageReport.objects.select_related("customer").prefetch_related("photos")
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        s = NoteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(DamageReportSerializer(resolve_damage(self.get_object(), request.user,
                                                              s.validated_data["note"])).data)


class ManagerClosedDayViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin,
                              viewsets.GenericViewSet):
    """POST {date, zone (empty = all zones), reason}: cancels that day's bookings free and
    tells customers to book again. DELETE reopens the day for new bookings."""

    permission_classes = [IsManager]
    serializer_class = ClosedDaySerializer
    queryset = ClosedDay.objects.select_related("zone")

    def create(self, request, *args, **kwargs):
        s = ClosedDaySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        n, closed = close_day(s.validated_data["date"], s.validated_data.get("zone"),
                              s.validated_data.get("reason", ""), request.user)
        return Response({**ClosedDaySerializer(closed).data, "cancelled_orders": n}, status=201)
