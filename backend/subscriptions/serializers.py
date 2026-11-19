from rest_framework import serializers

from orders.serializers import OrderSerializer

from .models import Subscription, SubscriptionPeriod, SubscriptionPlan


class PlanSerializer(serializers.ModelSerializer):
    """Manager: create / edit plans."""

    class Meta:
        model = SubscriptionPlan
        fields = ["id", "name", "washes_per_month", "services", "discount_percent", "sort_order", "is_active"]

    def validate_services(self, value):
        if not value:
            raise serializers.ValidationError("اختار خدمة واحدة على الأقل.")
        if any(s.is_oil_change for s in value):
            raise serializers.ValidationError("الباقة مينفعش يبقى فيها تغيير زيت.")
        return value

    def validate_washes_per_month(self, value):
        if not 1 <= value <= 8:
            raise serializers.ValidationError("من 1 لـ 8 غسلات في الشهر.")
        return value

    def validate_discount_percent(self, value):
        if value > 90:
            raise serializers.ValidationError("الخصم كبير قوي.")
        return value


class PeriodSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    visits = serializers.SerializerMethodField()
    hold_expires_at = serializers.SerializerMethodField()

    def get_visits(self, obj):
        qs = obj.visits.exclude(status="expired").order_by("scheduled_start")
        return OrderSerializer(qs, many=True).data

    def get_hold_expires_at(self, obj):
        o = obj.visits.filter(status="pending_payment").order_by("hold_expires_at").first()
        return o.hold_expires_at if o else None

    class Meta:
        model = SubscriptionPeriod
        fields = ["id", "number", "start_date", "end_date", "price", "normal_price", "wallet_used",
                  "payment_method", "status", "status_label", "makeup_visits", "paid_at", "hold_expires_at", "visits"]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    car_name = serializers.CharField(source="car.display_name", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    technician_name = serializers.CharField(source="technician.full_name", read_only=True, default=None)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    current = serializers.SerializerMethodField()
    service_ids = serializers.SerializerMethodField()

    def get_service_ids(self, obj):
        return [s.id for s in obj.plan.services.all()]

    def get_current(self, obj):
        from .service import current_period

        p = current_period(obj)
        return PeriodSerializer(p).data if p else None

    class Meta:
        model = Subscription
        fields = ["id", "plan", "plan_name", "car", "car_name", "address", "customer", "customer_name",
                  "customer_phone", "weekday", "start_time", "technician", "technician_name", "status",
                  "status_label", "renew", "created_at", "service_ids", "current"]
