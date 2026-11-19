from rest_framework import serializers

from .models import Referral


class ReferralSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    referee_name = serializers.CharField(source="referee.full_name", read_only=True)
    referee_phone = serializers.CharField(source="referee.phone", read_only=True)
    referrer_name = serializers.CharField(source="referrer.full_name", read_only=True)
    referrer_phone = serializers.CharField(source="referrer.phone", read_only=True)

    class Meta:
        model = Referral
        fields = ["id", "status", "status_label", "reason", "code", "referee", "referee_name", "referee_phone",
                  "referrer", "referrer_name", "referrer_phone", "first_order", "decided_at", "created_at"]
