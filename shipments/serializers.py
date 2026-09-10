from rest_framework import serializers
from .models import *
from decimal import Decimal
from accounts.serializers import UserSerializer
class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = "__all__"

class RateQuerySerializer(serializers.Serializer):
    service_type_id = serializers.PrimaryKeyRelatedField(queryset=ServiceType.objects.filter(is_active=True))
    weight_kg = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=Decimal("0.1"))
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=Decimal("0"))
    declared_value = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, min_value=Decimal("0"))

class RateResultSerializer(serializers.Serializer):
    service_name = serializers.CharField()
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    weight_charge = serializers.DecimalField(max_digits=10, decimal_places=2)
    distance_charge = serializers.DecimalField(max_digits=10, decimal_places=2)
    insurance_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    estimated_days = serializers.CharField()

class TrackingEventsSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")
    class Meta:
        model = TrackingEvent
        fields = ["id", "tracking_code", "status", "location", "description", "latitude", "longitude", "timestamp", "created_by_name"]


class ShipmentListSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service_type.name", read_only=True)
    latest_status = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = ["id", "shipment_code", "service_name", "sender_name", "receiver_name", "receiver_city", "receiver_state", "total_price", "is_paid", "status", "latest_status", "created_at", "weight_kg"]
        # fields = "__all__"

    def get_latest_status(self, obj):
        event = obj.tracking_events.first()
        return event.status if event else obj.status

class ShipmentDetailsSerializer(serializers.ModelSerializer):
    service_type = ServiceTypeSerializer(read_only=True)
    service_type_id = serializers.PrimaryKeyRelatedField(queryset=ServiceType.objects.filter(is_active=True), write_only=True, source="service_type",)
    tracking_events = TrackingEventsSerializer(many=True, read_only=True)
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Shipment
        fields = "__all__"
        read_only_fields  = [
            "id", "shipment_code", "sender", "quoted_price", "insurance_fee", "total_price", "is_paid", "status", "created_at", "updated_at"
        
        ]
    
    def create(self, validated_data):
        request = self.context["request"]
        validated_data["sender"] = request.user

        svc = validated_data["service_type"]
        weight = validated_data.get("weight_kg", 0)
        val = validated_data.get("declared_value", 0)

        distance = self.context.get("distance_km", 0)
        quoted = svc.base_price + (svc.price_per_kg * weight) + (svc.price_per_km * distance)
        insurance = round(float(val) * 0.01, 2)
        total = float(quoted) + insurance

        validated_data["quoted_price"] = quoted
        validated_data["insurance_fee"] = insurance
        validated_data["total_price"] = total
        return super().create(validated_data)

class PickUpSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickUpSlot
        fields = "__all__"
        read_only_fields = ["customer", "status"]


class ProofOfDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfDelivery
        fields = "__all__"
        read_only_fields = ["created_at", "delivered_at"]

class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = Review
        field = ["id", "shipment", "rating", "comment", "created_at", "customer_name"]
        read_only_fields = ["customer_name", "created_at"]

    def validate_ratings(self, value):
        if not (1 <=value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
