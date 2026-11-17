from rest_framework import serializers

from .models import HeardAboutOption, TermsVersion, User
from .phone import InvalidPhone, normalize_phone


class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        try:
            return normalize_phone(super().to_internal_value(data))
        except InvalidPhone as e:
            raise serializers.ValidationError(str(e))


class OtpRequestSerializer(serializers.Serializer):
    phone = PhoneField()
    device_id = serializers.CharField(max_length=100, required=False, allow_blank=True)


class OtpVerifySerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "الكود 6 أرقام."})
    # Needed only the first time (sign-up):
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    terms_version = serializers.IntegerField(required=False)
    device_type = serializers.ChoiceField(choices=User.DeviceType.choices, required=False)
    referral_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    heard_about = serializers.PrimaryKeyRelatedField(
        queryset=HeardAboutOption.objects.filter(is_active=True), required=False, allow_null=True
    )


class UserSerializer(serializers.ModelSerializer):
    needs_terms_acceptance = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "phone", "full_name", "role", "date_joined", "needs_terms_acceptance"]
        read_only_fields = ["id", "phone", "role", "date_joined"]


class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsVersion
        fields = ["version", "text", "created_at"]


class AcceptTermsSerializer(serializers.Serializer):
    terms_version = serializers.IntegerField()


class HeardAboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeardAboutOption
        fields = ["id", "label"]


class TechnicianSerializer(serializers.ModelSerializer):
    phone = PhoneField()

    class Meta:
        model = User
        fields = ["id", "phone", "full_name", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def validate_phone(self, value):
        qs = User.objects.filter(phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("الرقم ده متسجل قبل كده.")
        return value

    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("اسم الفني مطلوب.")
        return value.strip()

    def create(self, validated):
        return User.objects.create_user(role=User.Role.TECHNICIAN, **validated)
