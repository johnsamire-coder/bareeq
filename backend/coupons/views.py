from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsCustomer, IsManager
from orders.models import Order
from orders.serializers import OrderSerializer

from .models import Coupon
from .service import COUNTED, apply_coupon, remove_coupon


class CouponSerializer(serializers.ModelSerializer):
    times_used = serializers.SerializerMethodField()
    zone_name = serializers.CharField(source="zone.name", read_only=True, default=None)

    class Meta:
        model = Coupon
        fields = ["id", "code", "kind", "value", "expires_at", "max_uses_total", "max_uses_per_customer", "zone",
                  "zone_name", "is_active", "times_used", "created_at"]
        read_only_fields = ["created_at"]

    def get_times_used(self, obj):
        return obj.uses.filter(order__status__in=COUNTED).count()

    def validate_code(self, v):
        v = v.strip().upper()
        qs = Coupon.objects.filter(code__iexact=v)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("الكود ده موجود قبل كده.")
        return v

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        value = attrs.get("value", getattr(self.instance, "value", 0))
        if kind == "percent" and not 1 <= value <= 100:
            raise serializers.ValidationError({"value": "النسبة من 1 لـ 100."})
        if kind == "amount" and value < 100:
            raise serializers.ValidationError({"value": "المبلغ لازم يبقى جنيه على الأقل."})
        return attrs


class ManagerCouponViewSet(viewsets.ModelViewSet):
    """No delete: switch a coupon off with is_active=false (its history stays)."""

    permission_classes = [IsManager]
    serializer_class = CouponSerializer
    queryset = Coupon.objects.select_related("zone")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@api_view(["POST", "DELETE"])
@permission_classes([IsCustomer])
def order_coupon(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    if request.method == "DELETE":
        return Response(OrderSerializer(remove_coupon(order, request.user)).data)
    return Response(OrderSerializer(apply_coupon(order, request.user, request.data.get("code", ""))).data)
