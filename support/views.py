from django.shortcuts import render
from rest_framework import generics, permissions
from django.shortcuts import get_object_or_404
from .models import *
from .serializers import *
class SupportTicketListCreateView(generics.ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role in ("admin", "staff"):
            return SupportTicket.objects.all().prefetch_related("ticket_replies")
        return SupportTicket.objects.filter(user=self.request.user).prefetch_related("ticket_replies")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketReplyView(generics.CreateAPIView):
    serializer_class = TicketReplySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        ticket = get_object_or_404(SupportTicket, pk=self.kwargs["pk"])
        serializer.save(ticket=ticket, author=self.request.user)

