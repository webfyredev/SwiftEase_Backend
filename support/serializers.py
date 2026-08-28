from rest_framework import serializers
from .models import *
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