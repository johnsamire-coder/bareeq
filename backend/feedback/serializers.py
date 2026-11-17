from rest_framework import serializers

from scheduling.models import ClosedDay

from .models import DamageReport, Rating, RatingTag


class RatingTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingTag
        fields = ["id", "name", "sort_order", "is_active"]


class RatingInputSerializer(serializers.Serializer):
    stars = serializers.IntegerField()
    tags = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    call_requested = serializers.BooleanField(required=False, default=False)


class RatingSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source="technician.full_name", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)
    tag_names = serializers.SerializerMethodField()
    photo_count = serializers.IntegerField(source="photos.count", read_only=True)

    class Meta:
        model = Rating
        fields = ["id", "order", "stars", "tag_names", "comment", "call_requested", "technician", "technician_name",
                  "customer_name", "customer_phone", "zone_name", "photo_count", "created_at", "handled_at",
                  "handled_by", "handle_note"]

    def get_tag_names(self, obj):
        return [t.name for t in obj.tags.all()]


class DamageReportSerializer(serializers.ModelSerializer):
    photos = serializers.SerializerMethodField()
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)

    class Meta:
        model = DamageReport
        fields = ["id", "order", "description", "customer_phone", "created_at", "status", "resolved_at",
                  "resolved_by", "resolution_note", "photos"]

    def get_photos(self, obj):
        return [f"/api/damage-photos/{p.id}/file/" for p in obj.photos.all()]


class ClosedDaySerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True, default="كل المناطق")

    class Meta:
        model = ClosedDay
        fields = ["id", "date", "zone", "zone_name", "reason", "created_at"]
        extra_kwargs = {"reason": {"required": False, "allow_blank": True}}


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
