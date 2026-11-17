from django.db.models import Q
from rest_framework import serializers

from .models import CarBrand, CarColor, CarModel, CustomerCar, SizeClass


class CarBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarBrand
        fields = ["id", "name_en", "name_ar", "sort_order", "is_active"]


class CarModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarModel
        fields = ["id", "brand", "name", "size_class", "is_active"]

    def validate(self, attrs):
        brand = attrs.get("brand", getattr(self.instance, "brand", None))
        name = attrs.get("name", getattr(self.instance, "name", ""))
        qs = CarModel.objects.filter(brand=brand, name__iexact=name.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({"name": "الموديل ده موجود قبل كده في الماركة دي."})
        return attrs


class CarColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarColor
        fields = ["id", "name", "hex_code"]


class CustomerCarSerializer(serializers.ModelSerializer):
    brand = serializers.PrimaryKeyRelatedField(queryset=CarBrand.objects.filter(is_active=True))
    model = serializers.PrimaryKeyRelatedField(
        queryset=CarModel.objects.filter(is_active=True), required=False, allow_null=True
    )
    color = serializers.PrimaryKeyRelatedField(queryset=CarColor.objects.filter(is_active=True))
    # Only needed when the model is not in the list:
    size_class = serializers.ChoiceField(choices=SizeClass.choices, required=False)
    display_name = serializers.CharField(read_only=True)
    brand_name = serializers.CharField(source="brand.name_ar", read_only=True)
    color_name = serializers.CharField(source="color.name", read_only=True)

    class Meta:
        model = CustomerCar
        fields = [
            "id", "brand", "brand_name", "model", "unlisted_model_name", "size_class", "year", "color",
            "color_name", "plate_number", "parking", "needs_review", "display_name", "created_at",
        ]
        read_only_fields = ["needs_review", "created_at"]

    def validate(self, attrs):
        model = attrs.get("model", getattr(self.instance, "model", None))
        unlisted = attrs.get("unlisted_model_name", getattr(self.instance, "unlisted_model_name", "")).strip()
        if model is None:
            if not unlisted:
                raise serializers.ValidationError({"model": "اختار الموديل."})
            if not attrs.get("size_class", getattr(self.instance, "size_class", "")):
                raise serializers.ValidationError({"size_class": "اختار حجم العربية."})
        else:
            # Size comes from the catalog; ignore what the app sent.
            attrs.pop("size_class", None)
        attrs["unlisted_model_name"] = unlisted if model is None else ""
        return attrs


class ReviewUnlistedSerializer(serializers.Serializer):
    """Manager links a car with an unlisted model to an existing catalog model,
    or adds the model to the catalog (with the size the manager decides)."""

    model = serializers.PrimaryKeyRelatedField(queryset=CarModel.objects.all(), required=False)
    new_model_name = serializers.CharField(max_length=60, required=False)
    size_class = serializers.ChoiceField(choices=SizeClass.choices, required=False)

    def validate(self, attrs):
        if bool(attrs.get("model")) == bool(attrs.get("new_model_name")):
            raise serializers.ValidationError("اختار موديل موجود أو اكتب اسم موديل جديد.")
        if attrs.get("new_model_name") and not attrs.get("size_class"):
            raise serializers.ValidationError({"size_class": "حدد حجم الموديل الجديد."})
        return attrs


def search_filter(qs, term, fields):
    term = (term or "").strip()
    if not term:
        return qs
    q = Q()
    for f in fields:
        q |= Q(**{f + "__icontains": term})
    return qs.filter(q)
