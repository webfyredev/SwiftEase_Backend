from django.urls import path
from .views import *

urlpatterns = [
    # Srvices & Rates -----------------------------------------------------------

    path("services/", ServiceTypeListView.as_view(), name='service-list'),
    path("rate-calculator/", RateCalculatorView.as_view(), name='rate-calculator'),

    # Shipments -------------------------------------------------------------------

    path("shipments/", ShipmentListCreateView.as_view(), name='shipment-list'),
    path("shipments/<uuid:pk>/", ShipmentDetailView.as_view(), name='shipment-detail'),
    path("shipments/<uuid:pk>/events/", AddTrackingEventView.as_view(), name='tracking-events'),
    path("shipments/<uuid:pk>/labels/", ShipmentLabelView.as_view(), name='shipment-label'),
    path("shipments/<uuid:pk>/pod/", ProofOfDeliveryCreateView.as_view(), name='pod'),
    path("shipments/<uuid:pk>/review/", ReviewCreateView.as_view(), name='review'),
    path('dashboard/customer/', CustomerDashboardView.as_view(), name='customer-dashboard'),

    # Public tracking -----------------------------------------

    path("track/<str:code>/", PublicTrackView.as_view(), name='public-track'),

    # Pickup scheduling ----------------------------------------

    path("pickups/", PickUpSlotListCreateView.as_view(), name='pickup-list'),
    path("pickups/<int:pk>/", PickUpSlotDetailView.as_view(), name='pickup-detail'),

   
]
