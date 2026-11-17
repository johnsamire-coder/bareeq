from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsManager

from core.errors import BusinessError

from .geo import InvalidPolygon, point_in_polygon, polygons_overlap, validate_polygon
from .models import Address, AreaRequest, Zone
from .serializers import AddressSerializer, AreaRequestSerializer, PointSerializer, ZoneSerializer, ZoneShortSerializer
from .services import find_zone


class _ZonePermission(IsManager):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return super().has_permission(request, view)


class ZoneViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Everyone logged in sees active zones (the app can draw the covered area).
    Manager sees all and edits. No delete: switch off with is_active=false."""

    serializer_class = ZoneSerializer
    permission_classes = [_ZonePermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Zone.objects.all()
        if not IsManager().has_permission(self.request, self):
            qs = qs.filter(is_active=True)
        return qs

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Before saving a drawn shape: how many saved addresses fall inside, how many
        currently served addresses would drop OUT of service, and overlaps."""
        if not IsManager().has_permission(request, self):
            return Response({"code": "forbidden", "detail": "مش مسموح."}, status=403)
        try:
            polygon = validate_polygon(request.data.get("polygon"))
        except InvalidPolygon as e:
            raise BusinessError("bad_polygon", str(e))
        zone_id = request.data.get("zone")
        others = [z for z in Zone.objects.filter(is_active=True) if str(z.id) != str(zone_id)]
        inside = left_out = 0
        for a in Address.objects.filter(is_active=True).only("lat", "lng", "zone_id"):
            if point_in_polygon(a.lat, a.lng, polygon):
                inside += 1
            elif zone_id and str(a.zone_id) == str(zone_id) and not any(z.contains(a.lat, a.lng) for z in others):
                left_out += 1
        return Response({
            "addresses_inside": inside,
            "addresses_dropping_out": left_out,
            "overlaps_with": [z.name for z in others if polygons_overlap(polygon, z.polygon)],
        })


@api_view(["GET"])
@permission_classes([AllowAny])
def locate(request):
    """GET ?lat=&lng= : is this pin inside a service zone? Works before login too."""
    s = PointSerializer(data=request.query_params)
    s.is_valid(raise_exception=True)
    zone = find_zone(s.validated_data["lat"], s.validated_data["lng"])
    return Response({"covered": zone is not None, "zone": ZoneShortSerializer(zone).data if zone else None})


class MyAddressViewSet(viewsets.ModelViewSet):
    """The customer's saved addresses. Delete hides the address (orders keep it)."""

    serializer_class = AddressSerializer
    permission_classes = [IsCustomer]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Address.objects.filter(customer=self.request.user, is_active=True).select_related("zone")

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class AreaRequestViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """POST (customer): 'notify me when you arrive'. One open request per customer;
    a new one replaces the old location. GET (manager): the demand list."""

    serializer_class = AreaRequestSerializer

    def get_permissions(self):
        return [IsCustomer()] if self.request.method == "POST" else [IsManager()]

    def get_queryset(self):
        return AreaRequest.objects.select_related("customer")

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj, created = AreaRequest.objects.update_or_create(
            customer=request.user, notified_at__isnull=True, defaults=s.validated_data
        )
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
