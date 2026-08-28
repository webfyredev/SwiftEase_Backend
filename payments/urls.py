from django.urls import path
from .views import *

urlpatterns = [
    # Payments -----------------------------------------------------
    path("payments/initiate/", InitiatePaymentView.as_view(), name='initiate-payment'),
    path("payment/verify/", VerifyPaymentView.as_view(), name='verify-payment'),

    # Wallet -----------------------------------------------

    path("wallet/topup/", WalletTopUpView.as_view(), name='topup-wallet'),
    path("wallet/pay/", WalletPayView.as_view(), name = 'wallet-pay'),
    path("wallet/transactions/", WalletTransactionListView.as_view(), name='wallet-transactions'),

]
