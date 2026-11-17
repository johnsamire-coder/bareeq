from rest_framework import serializers

from .models import Setting


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ["key", "group", "label", "description", "value_type", "value", "updated_at"]
        read_only_fields = ["key", "group", "label", "description", "value_type", "updated_at"]

    def validate(self, attrs):
        # Run the model's type checks before saving.
        instance = self.instance
        instance.value = attrs.get("value", instance.value)
        instance.clean()
        return attrs
