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
                  "payment_method", "subtotal", "discount", "total", "items", "created_at"]


class ManagerOrderSerializer(OrderSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["customer", "customer_name", "customer_phone", "lat", "lng"]
