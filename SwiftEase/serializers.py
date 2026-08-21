from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import *

User = get_user_model()

class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    class Meta:
        model = User
        fields = ["email", "full_name", "phone", "password", "password2"]
    
    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password2" : "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "role", "avatar", "wallet_balance", "date_joined"]
        read_only_fields = ["id", "role", "wallet_balance", "date_joined"]

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validate_old_password["new_password"])
        user.save()
        
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ["user"]

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = "__all__"

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"

class DriverProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    class Meta:
        model = DriverProfile
        fields = "__all__"


class RateQuerySerializer(serializers.Serializer):
    service_type_id = serializers.PrimaryKeyRelatedField(queryset=ServiceType.objects.filter(is_active=True))
    weight_kg = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0.1)
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    declared_value = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, min_value=0)

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
        fields = ["id", "shipment_code", "service_name", "sender_name", "reciever_name", "receiver_city", "receiver_state", "total_price", "is_paid", "status", "latest_status", "created_at"]
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

class WalletTopupSerializer(serializers.ModelSerializer):
    class Meta:
        amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=100)
        reference = serializers.CharField(max_length=100)

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

class TicketReplySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    class Meta:
        model = TicketReply
        fields = ["ticket", "message", "author_name", "id", "created_at"]
        read_only_fields = ["author_name", "created_at"]

class SupportTicketSerializer(serializers.ModelSerializer):
    replies = TicketReplySerializer(many=True, read_only=True)
    user_name = serializers.CharField(source="user.full_name")
    class Meta:
        model = SupportTicket
        fields = ["id", "ticket_no", "user_name", "replies", "category", "shipment", "subject", "description", "created_at", "updated_at", "status"]
        read_only_fields = ["ticket_no", "status", "user_name"]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "notif_type", "is_read", "created_at"]
        read_only_fields = ["created_at"]
