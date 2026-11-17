from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsManager

from .models import CarBrand, CarColor, CarModel, CustomerCar, SizeClass, allowed_years
from .serializers import (
    CarBrandSerializer,
    CarColorSerializer,
    CarModelSerializer,
    CustomerCarSerializer,
    ReviewUnlistedSerializer,
    search_filter,
)


class _CatalogPermission(IsManager):
    """Anyone logged in reads; only the manager edits."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return super().has_permission(request, view)


def _is_manager(request):
    return IsManager().has_permission(request, None)


class CarBrandViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """GET ?search=  (Arabic or English name). Manager also sees hidden brands."""

    serializer_class = CarBrandSerializer
    permission_classes = [_CatalogPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = CarBrand.objects.all()
        if not _is_manager(self.request):
            qs = qs.filter(is_active=True)
        return search_filter(qs, self.request.query_params.get("search"), ["name_en", "name_ar"])


class CarModelViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """GET ?brand=<id>&search=. No delete: hide with is_active=false (old cars keep their model)."""

    serializer_class = CarModelSerializer
    permission_classes = [_CatalogPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = CarModel.objects.select_related("brand")
        if not _is_manager(self.request):
            qs = qs.filter(is_active=True, brand__is_active=True)
        brand = self.request.query_params.get("brand")
        if brand:
            qs = qs.filter(brand_id=brand)
        return search_filter(qs, self.request.query_params.get("search"), ["name"])


class CarColorViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = CarColor.objects.filter(is_active=True)
    serializer_class = CarColorSerializer
    permission_classes = [IsAuthenticated]


@api_view(["GET"])
@permission_classes([AllowAny])
def car_options(request):
    """Fixed choices for the add-car screens: years, sizes, parking places."""
    return Response(
        {
            "years": allowed_years(),
            "sizes": [{"value": v, "label": l} for v, l in SizeClass.choices],
            "parking": [{"value": v, "label": l} for v, l in CustomerCar.Parking.choices],
        }
    )


class MyCarViewSet(viewsets.ModelViewSet):
    """The logged-in customer's cars. Delete hides the car (orders keep pointing to it)."""

    serializer_class = CustomerCarSerializer
    permission_classes = [IsCustomer]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return CustomerCar.objects.filter(customer=self.request.user, is_active=True).select_related(
            "brand", "model", "color"
        )

    def _save(self, serializer, **extra):
        try:
            serializer.save(**extra)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

    def perform_create(self, serializer):
        self._save(serializer, customer=self.request.user)

    def perform_update(self, serializer):
        self._save(serializer)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class UnlistedCarViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Manager's review list: cars whose model was not in the catalog."""

    serializer_class = CustomerCarSerializer
    permission_classes = [IsManager]
    queryset = CustomerCar.objects.filter(needs_review=True, is_active=True).select_related("brand", "color")

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        car = self.get_object()
        s = ReviewUnlistedSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        with transaction.atomic():
            model = s.validated_data.get("model")
            if model is None:
                model, _ = CarModel.objects.get_or_create(
                    brand=car.brand,
                    name=s.validated_data["new_model_name"].strip(),
                    defaults={"size_class": s.validated_data["size_class"]},
                )
            if model.brand_id != car.brand_id:
                raise ValidationError({"model": "الموديل ده مش تبع ماركة العربية."})
            # Other cars with the same unlisted name get linked too.
            same = CustomerCar.objects.filter(
                needs_review=True, brand=car.brand, unlisted_model_name__iexact=car.unlisted_model_name
            )
            linked = 0
            for c in same:
                c.model = model
                c.save()
                linked += 1
        return Response({"model": CarModelSerializer(model).data, "cars_linked": linked}, status=status.HTTP_200_OK)
