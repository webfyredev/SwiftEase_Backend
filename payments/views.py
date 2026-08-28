import requests
from django.shortcuts import render
from rest_framework import views, permissions, generics
from django.shortcuts import get_object_or_404
from shipments.models import Shipment
from rest_framework.response import Response
from .serializers import *
from .services import *
class InitiatePaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        shipment_id = request.data.get("shipment_id")
        shipment = get_object_or_404(Shipment, id=shipment_id, sender=request.user)

        if shipment.is_paid:
            return Response({"detail" : "Shipment already paid."}, status=400)

        data = initialize_paystack_payment(shipment, request.user)
        return Response(data)

class VerifyPaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reference = request.query_params.get("reference")
        if not reference:
            return Response({"detail" : "reference is required."}, status=400)
        payment = verify_paystack_payment(reference)
        return Response(PaymentSerializer(payment).data)

class WalletTopUpView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WalletTopupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ref = serializer.validated_data["reference"]
        amount = float(serializer.validated_data["amount"])

        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{ref}",
            headers={"Authorization" : f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=15,
        )

        data = response.json()["data"]
        if data["status"] != "success":
            return Response({"detail" : "Payment not successful"}, status=400)
        from .services import credit_wallet

        txn = credit_wallet(request.user, amount, f"Wallet top-up via Paystack ref {ref}")
        return Response(WalletTransactionSerializer(txn).data)

class WalletPayView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shipment = get_object_or_404(Shipment, id=request.data.get("shipment_id"), sender=request.user)
        try:
            payment = pay_with_wallet(shipment, request.user)
        except ValueError as e:
            return Response({"detail" : str(e)}, status=400)
        return Response(PaymentSerializer(payment).data)

class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(user=self.request.user)


