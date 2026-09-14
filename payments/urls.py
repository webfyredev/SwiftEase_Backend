from django.urls import path
from .views import *

urlpatterns = [
    # Payments -----------------------------------------------------
    path("initiate/", InitiatePaymentView.as_view(), name='initiate-payment'),
    path("verify/", VerifyPaymentView.as_view(), name='verify-payment'),

    # Wallet -----------------------------------------------

    path("wallet/", WalletSummaryView.as_view(), name='wallet-summary'),
    path("wallet/topup/init/", WalletTopUpInitView.as_view(), name = 'wallet-topup-init'),
    path("wallet/topup/verify/", WalletTopupVerifyView.as_view(), name = 'wallet-topup-verify'),
    path("wallet/pay/", WalletPayShipmentView.as_view(), name = 'wallet-pay'),
    path("wallet/transactions/", WalletTransactionListView.as_view(), name = 'wallet-transactions'),
]
