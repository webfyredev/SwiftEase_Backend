from django.urls import path
from .views import *

urlpatterns = [
    path("support/", SupportTicketListCreateView.as_view(), name='Ticket_list'),
    path("support/<uuid:pk>/reply/", TicketReplyView.as_view(), name='ticket_reply'),
]
