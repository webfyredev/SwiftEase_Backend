from django.urls import path
from .views import *

urlpatterns = [
    path('overview/', AdminOverviewView.as_view(), name='admin-dashboard'),
    path('shipments/', AdminShipmentListView.as_view(), name='shipment-list'),
    path('shipments/<uuid:pk>/', AdminShipmentDetailView.as_view(), name='shipments-details'),
    path('shipments/<uuid:pk>/status/', AdminUpdateShipmentStatusView.as_view(), name='update-shipments'),
    path('shipments/<uuid:pk>/assign/', AdminAssignDriverView.as_view(), name='assign-driver'),
    path('drivers/', AdminDriverListView.as_view(), name='drivers'),
    path('tickets/', AdminTicketListView.as_view(), name='tickets-list'),
    path('tickets/<uuid:pk>/', AdminTicketDetailView.as_view(), name='ticket-details'),
    path('tickets/<uuid:pk>/reply/', AdminTicketReplyView.as_view(), name='ticket-reply'),
    path('tickets/<uuid:pk>/status/', AdminTicketUpdateStatusView.as_view(), name='ticket-status'),
]