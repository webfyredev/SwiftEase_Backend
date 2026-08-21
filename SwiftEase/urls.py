from django.urls import path
from .views import *
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, TokenBlacklistView)


urlpatterns = [
    # Auth -------------------------------------------------------------------
    path("auth/register/", RegisterView.as_view(), name='register'),
    path("auth/login/", TokenObtainPairView.as_view(), name='login'),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name='refresh'),
    path("auth/logout/", TokenBlacklistView.as_view(), name='logout'),
    path("auth/profile/", ProfileView.as_view(), name="profile"),
    path("auth/change-password/", ChangePasswordView.as_view(), name='reset-password'),

    # Addresses --------------------------------------------------------------

    path("addresses/", AddressListCreateView.as_view(), name='address-list'),
    path("addresses/<int:pk>/", AddressDetailView.as_view(), name='address-detail'),

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

    # Public tracking -----------------------------------------

    path("track/<str:code>/", PublicTrackView.as_view(), name='public-track'),

    # Pickup scheduling ----------------------------------------

    path("pickups/", PickUpSlotListCreateView.as_view(), name='pickup-list'),
    path("pickups/<int:pk>/", PickUpSlotDetailView.as_view(), name='pickup-detail'),

    # Payments -----------------------------------------------------
    path("payments/initiate/", InitiatePaymentView.as_view(), name='initiate-payment'),
    path("payment/verify/", VerifyPaymentView.as_view(), name='verify-payment'),

    # Wallet -----------------------------------------------

    path("wallet/topup/", WalletTopUpView.as_view(), name='topup-wallet'),
    path("wallet/pay/", WalletPayView.as_view(), name = 'wallet-pay'),
    path("wallet/transactions/", WalletTransactionListView.as_view(), name='wallet-transactions'),

    # Support Tickets -------------------------------------------------

    path("support/", SupportTicketListCreateView.as_view(), name='Ticket_list'),
    path("support/<uuid:pk>/reply/", TicketReplyView.as_view(), name='ticket_reply'),

    # Notifications ---------------------------------------------------

    path("notifications/", NotificationListView.as_view(), name='notification-list'),
    path("notifications/read-all/", MarkAllReadView.as_view(), name='notification-read-all'),
    path("notifications/<int:pk>/read/", MarkNotificationReadView.as_view(), name='notification-read'),

    # Driver -----------------------------------------------------------------

    path("driver/location/", DriverLocationUpdateView.as_view(), name='driver-location'),
    path("driver/shipments/", DriverShipmentsView.as_view(), name='driver-shipments'),

    # Admin Dashboard ---------------------------------------------------

    path("admin/dashboard", AdminDashboardView.as_view(), name='admin-dashboard'),
    path("admin/shipments/", AdminShipmentListView.as_view(), name='admin-shipments')
]   

