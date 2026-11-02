from django.urls import path
from .views import *

urlpatterns = [
    path('dashboard/', DriverDashboardView.as_view(), name='driver-dashboard'),
    path('duty/', ToggleDutyView.as_view(), name='driver-duty'),
    path('shipments/', DriverShipmentsView.as_view(), name='driver-shipments'),
    path('shipments/<int:pk>/', DriverShipmentDetailView.as_view(), name='driver-shipment_details'),
    path('shipments/<int:pk>/status/', UpdateShipmentStatusView.as_view(), name='driver-shipment-status'),
    path('shipments/<int:pk>/pod/', SubmitProofOfDeliveryView.as_view(), name='driver-pod'),
    path('location/', DriverLocationUpdateView.as_view(), name='driver-location')
]
