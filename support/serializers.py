from rest_framework import serializers
from .models import *
from accounts.serializers import UserSerializer


class TicketReplySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    is_staff  = serializers.SerializerMethodField()
    class Meta:
        model = TicketReply
        fields = ["id", "author_name","message", "is_staff", "created_at"]
        read_only_fields = ["author_name", "is_staff", "created_at"]

    def get_is_staff(self, obj):
        return obj.author.role in ("admin", "staff")


class SupportTicketSerializer(serializers.ModelSerializer):
    replies = TicketReplySerializer(source="ticket_replies", many=True, read_only=True)

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    shipment_code = serializers.CharField(source="shipment.shipment_code", read_only=True, default=None)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    class Meta:
        model = SupportTicket
        fields = ["id", "ticket_no", "user_name", "category", "category_display", "shipment", "shipment_code", "subject", "description", "status", "status_display", "replies", "created_at", "updated_at",]
        read_only_fields = ["ticket_no", "status", "user_name", "shipment_code", "category_display", "status_display"]