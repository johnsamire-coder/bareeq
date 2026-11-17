from rest_framework import serializers

from .models import DayOff, TechnicianProfile, WeeklyShift


class WeeklyShiftSerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = WeeklyShift
        fields = ["id", "technician", "weekday", "weekday_label", "start_time", "end_time"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "وقت النهاية لازم يبقى بعد البداية."})
        return attrs


class DayOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayOff
        fields = ["id", "technician", "date", "reason"]


class TechnicianProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.full_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    shifts = WeeklyShiftSerializer(many=True, read_only=True)

    class Meta:
        model = TechnicianProfile
        fields = ["id", "user", "name", "phone", "is_active", "zones", "start_label", "start_lat", "start_lng",
                  "shifts"]
        read_only_fields = ["user"]
