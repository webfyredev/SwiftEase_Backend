from django.urls import path
from .views import *

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name='notification-list'),
    path("notifications/read-all/", MarkAllReadView.as_view(), name='notification-read-all'),
    path("notifications/<int:pk>/read/", MarkNotificationReadView.as_view(), name='notification-read'),
]
