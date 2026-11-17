from rest_framework import serializers

from .models import Order, OrderItem


class BookingItemSerializer(serializers.Serializer):
    car = serializers.IntegerField()
    services = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    oil_type = serializers.IntegerField(required=False, allow_null=True)


class SlotsRequestSerializer(serializers.Serializer):
    address = serializers.IntegerField()
    items = BookingItemSerializer(many=True)


class CreateOrderSerializer(SlotsRequestSerializer):
    start = serializers.DateTimeField()


class ConfirmSerializer(serializers.Serializer):
    payment_method = serializers.CharField()


class ReassignSerializer(serializers.Serializer):
    technician = serializers.IntegerField()
    force = serializers.BooleanField(default=False)


class OrderItemSerializer(serializers.ModelSerializer):
    car_name = serializers.CharField(source="car.display_name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["car", "car_name", "size_class", "minutes", "total", "quote"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    technician_name = serializers.CharField(source="technician.full_name", read_only=True, default=None)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "status_label", "scheduled_start", "scheduled_end", "total_minutes",
                  "hold_expires_at", "zone", "zone_name", "address", "technician", "technician_name",
                  "payment_method", "subtotal", "discount", "total", "charges_total", "amount_due", "items",
                  "actual_start", "actual_end", "cancel_reason", "created_at"]


class ManagerOrderSerializer(OrderSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["customer", "customer_name", "customer_phone", "lat", "lng"]


class PointSerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


class PhotoUploadSerializer(serializers.Serializer):
    stage = serializers.CharField()
    side = serializers.CharField()
    image = serializers.FileField()
    captured_at = serializers.DateTimeField()
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6)
    accuracy_m = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class OrderPhotoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    stage = serializers.CharField()
    side = serializers.CharField()
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    captured_at = serializers.DateTimeField()
    uploaded_at = serializers.DateTimeField()
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6)
    accuracy_m = serializers.IntegerField(allow_null=True)
    flags = serializers.ListField()
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return f"/api/order-photos/{obj.id}/file/"


class RescheduleSerializer(serializers.Serializer):
    start = serializers.DateTimeField()


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CustomerChargeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kind = serializers.CharField()
    label = serializers.CharField(source="get_kind_display")
    amount = serializers.IntegerField()
    source_order = serializers.IntegerField(source="source_order_id")
    applied_to_order = serializers.IntegerField(source="applied_to_order_id", allow_null=True)
    created_at = serializers.DateTimeField()
    waived_at = serializers.DateTimeField(allow_null=True)
    waived_by = serializers.IntegerField(source="waived_by_id", allow_null=True)
    waive_reason = serializers.CharField()
    customer = serializers.IntegerField(source="customer_id")
    customer_phone = serializers.CharField(source="customer.phone")
