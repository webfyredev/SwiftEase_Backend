from django.urls import path
from .views import *

urlpatterns = [
    path("tickets/", SupportTicketListCreateView.as_view(), name='ticket-list-create'),
    path("tickets/<uuid:pk>/", SupportTicketDetailView.as_view(), name='ticket-details'),
    path("ticket/<uuid:pk>/reply/", TicketReplyCreateView.as_view(), name='ticket-reply'),
    path("my-shipments/", CustomerShipmentForTicketView.as_view(), name='ticket-shipments'),
]
