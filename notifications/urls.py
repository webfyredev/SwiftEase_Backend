from django.urls import path
from .views import *

urlpatterns = [
    path("", NotificationListView.as_view(), name='notification-list'),
    path("unread-count/", NotificationUnreadCountView.as_view(), name='notification-unread'),
    path("read-all/", MarkAllReadView.as_view(), name='notification-read-all'),
    path("<int:pk>/read/", MarkNotificationReadView.as_view(), name='notification-read'),
    path("<int:pk>/delete/", DeleteNotificationView.as_view(), name='notification-delete'),

]
