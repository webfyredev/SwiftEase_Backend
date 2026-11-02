from django.shortcuts import render
from rest_framework import generics, permissions, views
from .models import *
from .serializers import *
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)

        notif_type = self.request.query_params.get("type")
        if notif_type:
            qs = qs.filter(notif_type=notif_type)
        unread = self.request.query_params.get("unread")
        if unread == "true":
            qs = qs.filter(is_read=False)

        return qs

class NotificationUnreadCountView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count" : count })

    
class MarkNotificationReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return Response({"detail" : "Marked as read"})

class MarkAllReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail" : "All notification marked as read.", "updated" : updated})

class DeleteNotificationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.delete()
        return Response({"detail" : "Notification deleted."}, status=204)
