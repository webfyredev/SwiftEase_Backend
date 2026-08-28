from .models import *
from rest_framework import serializers
from decimal import Decimal
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["reference", "status", "gateway_response", "paid_at"]

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = "__all__"
        read_only_fields = ["user", "balance_after", "created_at"]

class WalletTopupSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("100"))
    reference = serializers.CharField(max_length=100)
