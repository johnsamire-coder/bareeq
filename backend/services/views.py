from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import IsManager
from cars.models import CustomerCar
from core.errors import BusinessError
from places.models import Address, Zone

from .models import Bundle, OilType, Service, ServiceDuration, ServicePrice
from .pricing import build_quote
from .serializers import (
    BundleSerializer,
    ContextSerializer,
    OilTypeSerializer,
    QuoteRequestSerializer,
    ServiceDurationSerializer,
    ServicePriceSerializer,
    ServiceSerializer,
)


def _resolve_context(request, data):
    """Returns (zone, size_class, parking)."""
    if data.get("address") or data.get("car"):
        user = request.user
        if not (user.is_authenticated and user.role == "customer"):
            raise BusinessError("login_required", "سجل دخول الأول.", status=401)
        address = Address.objects.filter(pk=data.get("address"), customer=user, is_active=True).first()
        car = CustomerCar.objects.filter(pk=data.get("car"), customer=user, is_active=True).first()
        if address is None or car is None:
            raise BusinessError("address_and_car_required", "اختار العنوان والعربية.")
        if address.zone is None or not address.zone.is_active:
            raise BusinessError("outside_service_area", "العنوان ده برا المناطق اللي بنخدمها دلوقتي.")
        return address.zone, car.size_class, car.parking
    zone = Zone.objects.filter(pk=data.get("zone"), is_active=True).first()
    if zone is None or not data.get("size_class"):
        raise BusinessError("zone_and_size_required", "حدد المنطقة وحجم العربية.")
    return zone, data["size_class"], data.get("parking")


@api_view(["GET"])
@permission_classes([AllowAny])
def catalog(request):
    """Services screen: every active service with its price and minutes for this
    zone and car size, plus bundles and oil types. Services without a price
    here are left out."""
    s = ContextSerializer(data=request.query_params)
    s.is_valid(raise_exception=True)
    zone, size, parking = _resolve_context(request, s.validated_data)

    prices = {p.service_id: p for p in ServicePrice.objects.filter(zone=zone, size_class=size)}
    minutes = {d.service_id: d.minutes for d in ServiceDuration.objects.filter(size_class=size)}
    services = []
    for svc in Service.objects.filter(is_active=True).prefetch_related("replaces"):
        if svc.id in prices and svc.id in minutes:
            services.append({
                "id": svc.id, "code": svc.code, "name": svc.name, "description": svc.description,
                "category": svc.category, "category_label": svc.get_category_display(),
                "price": prices[svc.id].price, "minutes": minutes[svc.id],
                "needs_shade": svc.needs_shade, "is_oil_change": svc.is_oil_change,
                "replaces": [r.id for r in svc.replaces.all()],
            })
    available = {x["id"] for x in services}
    bundles = []
    for b in Bundle.objects.filter(is_active=True).prefetch_related("services"):
        ids = [x.id for x in b.services.all()]
        if ids and set(ids) <= available:
            bundles.append({"id": b.id, "name": b.name, "description": b.description, "services": ids,
                            "discount_percent": b.discount_percent})
    return Response({
        "zone": {"id": zone.id, "name": zone.name},
        "size_class": size,
        "parking": parking,
        "services": services,
        "bundles": bundles,
        "oil_types": OilTypeSerializer(OilType.objects.filter(is_active=True), many=True).data,
        "has_provisional_prices": any(prices[i].is_provisional for i in available),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def quote(request):
    """Live total for the sticky bar and the summary screen."""
    s = QuoteRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    zone, size, parking = _resolve_context(request, s.validated_data)
    return Response(build_quote(s.validated_data["services"], zone, size, parking, s.validated_data.get("oil_type")))


class _ManagerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManager]
    http_method_names = ["get", "post", "patch", "head", "options"]  # no delete: switch off instead


class ManageServiceViewSet(_ManagerViewSet):
    queryset = Service.objects.prefetch_related("replaces")
    serializer_class = ServiceSerializer


class ManagePriceViewSet(_ManagerViewSet):
    """GET ?zone=&service=. PATCH {price} (piastres) also clears the 'provisional' mark."""

    serializer_class = ServicePriceSerializer

    def get_queryset(self):
        qs = ServicePrice.objects.all()
        for f in ("zone", "service", "size_class"):
            v = self.request.query_params.get(f)
            if v:
                qs = qs.filter(**{f: v})
        return qs

    @action(detail=False, methods=["post"], url_path="confirm-all")
    def confirm_all(self, request):
        n = ServicePrice.objects.filter(is_provisional=True).update(is_provisional=False)
        return Response({"confirmed": n})


class ManageDurationViewSet(_ManagerViewSet):
    queryset = ServiceDuration.objects.all()
    serializer_class = ServiceDurationSerializer


class ManageBundleViewSet(_ManagerViewSet):
    queryset = Bundle.objects.prefetch_related("services")
    serializer_class = BundleSerializer


class ManageOilTypeViewSet(_ManagerViewSet):
    queryset = OilType.objects.all()
    serializer_class = OilTypeSerializer
