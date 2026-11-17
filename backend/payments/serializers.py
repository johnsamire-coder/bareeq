from rest_framework import serializers

from .models import DailyClosing, Invoice, Material, Payment, WalletEntry


class WalletEntrySerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = WalletEntry
        fields = ["id", "kind", "kind_label", "amount", "remaining", "expires_at", "order", "note", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    customer_name = serializers.CharField(source="order.customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="order.customer.phone", read_only=True)
    proof_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "order", "method", "amount", "status", "status_label", "customer_name", "customer_phone",
                  "proof_url", "reviewed_by", "reviewed_at", "review_reason", "created_at"]

    def get_proof_url(self, obj):
        return f"/api/payment-proofs/{obj.id}/file/" if obj.proof else None


class InvoiceSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    # Revenue next to real money (cash + InstaPay); the difference is the wallet.
    revenue = serializers.IntegerField(source="total", read_only=True)
    collected = serializers.SerializerMethodField()

    def get_collected(self, obj):
        return obj.cash_amount + obj.instapay_amount

    class Meta:
        model = Invoice
        fields = ["id", "number", "order", "issued_at", "lines", "subtotal", "discount", "oil_total",
                  "charges_total", "total", "revenue", "collected", "wallet_amount", "instapay_amount", "cash_amount",
                  "status",
                  "status_label", "cancelled_at", "cancelled_by", "cancel_reason"]


class MaterialSerializer(serializers.ModelSerializer):
    unit_label = serializers.CharField(source="get_unit_display", read_only=True)

    class Meta:
        model = Material
        fields = ["id", "name", "unit", "unit_label", "unit_cost", "sort_order", "is_active"]


class DailyClosingSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source="technician.full_name", read_only=True)

    class Meta:
        model = DailyClosing
        fields = ["id", "technician", "technician_name", "date", "cash_expected", "cash_handed", "difference",
                  "note", "status", "submitted_at", "confirmed_by", "confirmed_at"]


class MaterialItemSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    quantity = serializers.CharField()


class MaterialsSerializer(serializers.Serializer):
    items = MaterialItemSerializer(many=True)


class SubmitClosingSerializer(serializers.Serializer):
    date = serializers.DateField()
    cash_handed = serializers.IntegerField(min_value=0)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ManualCreditSerializer(serializers.Serializer):
    customer = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)
    note = serializers.CharField()


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
