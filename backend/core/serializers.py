from rest_framework import serializers

from .models import Setting


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ["key", "group", "label", "description", "value_type", "value", "allow_empty", "mentioned_in_terms",
                  "updated_at"]
        read_only_fields = ["key", "group", "label", "description", "value_type", "allow_empty", "mentioned_in_terms",
                            "updated_at"]
        extra_kwargs = {"value": {"allow_null": True}}

    def validate(self, attrs):
        # Run the model's type checks before saving.
        instance = self.instance
        instance.value = attrs.get("value", instance.value)
        instance.clean()
        return attrs
