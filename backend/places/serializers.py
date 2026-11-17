from rest_framework import serializers

from core.errors import BusinessError

from .geo import InvalidPolygon, validate_polygon
from .models import Address, AreaRequest, Zone
from .services import find_zone


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "name", "polygon", "is_active", "sort_order"]

    def validate_polygon(self, value):
        try:
            return validate_polygon(value)
        except InvalidPolygon as e:
            raise serializers.ValidationError(str(e))


class ZoneShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "name"]


class PointSerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)


class AddressSerializer(serializers.ModelSerializer):
    zone = ZoneShortSerializer(read_only=True)

    class Meta:
        model = Address
        fields = ["id", "label", "lat", "lng", "zone", "street", "building", "floor", "apartment", "landmark", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        lat = attrs.get("lat", getattr(self.instance, "lat", None))
        lng = attrs.get("lng", getattr(self.instance, "lng", None))
        zone = find_zone(lat, lng)
        if zone is None:
            raise BusinessError("outside_service_area", "لسه مش بنخدم المكان ده. تقدر تطلب إننا نبلغك أول ما نوصل.")
        attrs["zone"] = zone
        for field in ("label", "building"):
            if field in attrs and not attrs[field].strip():
                raise serializers.ValidationError({field: "مطلوب."})
        return attrs


class AreaRequestSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    now_covered_by = serializers.SerializerMethodField()

    class Meta:
        model = AreaRequest
        fields = ["id", "lat", "lng", "area_name", "customer_name", "customer_phone", "created_at", "notified_at",
                  "now_covered_by"]
        read_only_fields = ["created_at", "notified_at"]

    def get_now_covered_by(self, obj):
        zone = find_zone(obj.lat, obj.lng)
        return zone.name if zone else None

    def validate(self, attrs):
        if find_zone(attrs["lat"], attrs["lng"]) is not None:
            raise BusinessError("inside_service_area", "المكان ده إحنا بنخدمه بالفعل. تقدر تضيفه كعنوان.")
        return attrs
