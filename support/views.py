from django.shortcuts import render
from rest_framework import generics, permissions, views, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import *
from .serializers import *
from shipments.models import Shipment


class SupportTicketListCreateView(generics.ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("admin", "staff"):
            qs = SupportTicket.objects.all()
        else:
            qs = SupportTicket.objects.filter(user=user)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.select_related("user", "shipment", "assigned_to").prefetch_related("ticket_replies__author").order_by("-created_at")
        

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SupportTicketDetailView(generics.RetrieveAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("admin", "staff"):
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=user)

    def get_object(self):
        qs = self.get_queryset()
        obj = get_object_or_404(qs.select_related("user", "shipment").prefetch_related("ticket_replies__author"))
        return obj

class TicketReplyCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        if user.role in ("admin", "staff"):
            ticket = get_object_or_404(SupportTicket, pk=pk)
        else:
            ticket = get_object_or_404(SupportTicket, pk=pk, user=user)

        message = request.data.get("message", "").strip()
        if not message:
            return Response({"detail" : "Message cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        reply = TicketReply.objects.create(ticket=ticket, author=user, message=message)

        if reply.status == "resolved" and user.role == "customer":
            ticket.status = "open"
            ticket.save(update_fields=["status"])

        return Response(TicketReplySerializer(reply).data, status=status.HTTP_201_CREATED)


class CustomerShipmentForTicketView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        shipments = Shipment.objects.filter(sender=request.user).order_by("-created_at").values("id", "shipment_code", "receiver_city", "status")

        return Response([
            {
                "id" : str(s["id"]),
                "shipment_code" : s["shipment_code"],
                "receiver_city" : s["receiver_city"],
                "status" : s["status"]
            } for s in shipments
        ])