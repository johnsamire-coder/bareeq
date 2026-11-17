from rest_framework import serializers

from cars.models import SizeClass

from .models import Bundle, OilType, Service, ServiceDuration, ServicePrice


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "code", "name", "description", "category", "price_depends_on_size", "needs_shade",
                  "replaces", "is_oil_change", "sort_order", "is_active"]

    def validate(self, attrs):
        replaces = attrs.get("replaces") or []
        if self.instance and self.instance in replaces:
            raise serializers.ValidationError({"replaces": "الخدمة مينفعش تلغي نفسها."})
        return attrs


class ServicePriceSerializer(serializers.ModelSerializer):
    price_pounds = serializers.SerializerMethodField()

    class Meta:
        model = ServicePrice
        fields = ["id", "service", "zone", "size_class", "price", "price_pounds", "is_provisional", "updated_at"]
        read_only_fields = ["is_provisional", "updated_at"]

    def get_price_pounds(self, obj):
        return obj.price / 100

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:  # only the price can change on an existing row
            for f in ("service", "zone", "size_class"):
                fields[f].read_only = True
        return fields

    def save(self, **kwargs):
        # A price typed by the manager is a real price.
        return super().save(is_provisional=False, **kwargs)


class ServiceDurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceDuration
        fields = ["id", "service", "size_class", "minutes", "updated_at"]
        read_only_fields = ["updated_at"]


class BundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bundle
        fields = ["id", "name", "description", "services", "discount_percent", "sort_order", "is_active"]

    def validate_services(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("الباقة لازم يكون فيها خدمتين على الأقل.")
        return value


class OilTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OilType
        fields = ["id", "name", "description", "price", "sort_order", "is_active"]


class ContextSerializer(serializers.Serializer):
    """Either zone + size_class (+ parking), or the customer's own address + car."""

    zone = serializers.IntegerField(required=False)
    size_class = serializers.ChoiceField(choices=SizeClass.choices, required=False)
    parking = serializers.CharField(required=False)
    address = serializers.IntegerField(required=False)
    car = serializers.IntegerField(required=False)


class QuoteRequestSerializer(ContextSerializer):
    services = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    oil_type = serializers.IntegerField(required=False, allow_null=True)
