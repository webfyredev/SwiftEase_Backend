from django.urls import path
from .views import *

urlpatterns = [
    # Srvices & Rates -----------------------------------------------------------

    path("services/", ServiceTypeListView.as_view(), name='service-list'),
    path("rate/", RateCalculatorView.as_view(), name='rate-calculator'),

    # Shipments -------------------------------------------------------------------

    path("", ShipmentListCreateView.as_view(), name='shipment-list'),
    path("<uuid:pk>/", ShipmentDetailView.as_view(), name='shipment-detail'),
    path("<uuid:pk>/events/", AddTrackingEventView.as_view(), name='tracking-events'),
    path("<uuid:pk>/labels/", ShipmentLabelView.as_view(), name='shipment-label'),
    path("<uuid:pk>/pod/", ProofOfDeliveryCreateView.as_view(), name='pod'),
    path("<uuid:pk>/review/", ReviewCreateView.as_view(), name='review'),
    path('dashboard/customer/', CustomerDashboardView.as_view(), name='customer-dashboard'),

    # Public tracking -----------------------------------------

    path("track/<str:code>/", PublicTrackView.as_view(), name='public-track'),
    path("track/auth/<str:code>/", AuthenticatedTrackView.as_view(), name='auth-track'),

    # Pickup scheduling ----------------------------------------
    path("pickups/dashboard/", PickupDashboardView.as_view(), name='pickup-dashboard'),
    path("pickups/", PickUpSlotListCreateView.as_view(), name='pickup-list'),
    path("pickups/<int:pk>/", PickUpSlotDetailView.as_view(), name='pickup-detail'),
    path("pickups/<int:pk>/cancel/", CancelPickUpView.as_view(), name='cancel-pickups')

   
]
