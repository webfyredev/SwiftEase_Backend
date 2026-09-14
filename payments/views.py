import requests
from django.shortcuts import render
from rest_framework import views, permissions, generics, status
from django.shortcuts import get_object_or_404
from shipments.models import Shipment
from rest_framework.response import Response
from .serializers import *
from .services import *
from .models import *
from django.conf import settings



class WalletTopUpInitView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WalletTopupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ref = serializer.validated_data["reference"]
        amount = float(serializer.validated_data["amount"])
        user = request.user
        import uuid
        reference = f"WLTOPUP-{uuid.uuid4().hex[:12].upper()}"
        amount_kobo = int(amount * 100)

        try:
            response = requests.post("https://api.paystack.co/transaction/initialize", json={
                "email" : user.email,
                "amount" : amount_kobo,
                "reference" : reference,
                "metadata" : {
                    "topup" : True,
                    "user_id" : (user.id),
                    "amount" : amount,
                },
                "callback_url" : f"{settings.FRONTEND_URL}/customer/wallet?ref={reference}"
            },
            headers={
                "Authorization" : f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type" : "application/json",
            },
            timeout=15
            )
            response.raise_for_status()
            data = response.json()['data']
        except Exception as e:
            return Response({
                "detail" : "Could not reach payment provider. Try again."
            }, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "authorization_url" : data['authorization_url'],
            "reference" : reference,
            "amount" : amount
        })
        
class WalletTopupVerifyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reference = request.query_params.get("reference")
        if not reference:
            return Response({"detail" : "reference is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers={"Authorization" : f"Bearer {settings.PAYSTACK_SECRET_KEY}",}, timeout=15,)
            response.raise_for_status()
            data = response.json()["data"]
        except Exception:
            return Response({"detail" : "Could not verify payment."}, status=status.HTTP_502_BAD_GATEWAY)

        if data["status"] != "success":
            return Response({"detail" : "Payment was not successful.", "status" : data['status']}, status=status.HTTP_400_BAD_REQUEST)
        if not reference.startswith("WLTOPUP-"):
            return Response({
                "detail" : "Invalid Reference type"
            }, status=status.HTTP_400_BAD_REQUEST)

        already = WalletTransaction.objects.filter(description__icontains=reference).exists()
        if already:
            return Response({"detail" : "This top-up was already processed."}, status=status.HTTP_400_BAD_REQUEST)

        amount_naira = data["amount"] / 100
        txn = credit_wallet(user= request.user, amount=amount_naira, description=f"Wallet top-up via Paystack ref {reference}",)

        request.user.refresh_from_db()

        return Response({
            "detail" : "Wallet credited successfully.",
            "amount_credited" : amount_naira,
            "new_balance" : str(request.user.wallet_balance),
            "transaction" : WalletTransactionSerializer(txn).data,
        })

class WalletPayShipmentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shipment_id = request.data.get("shipment_id")
        if not shipment_id:
            return Response({
                "detail" : "shipment_id is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        shipment = get_object_or_404(Shipment, id=shipment_id, sender=request.user)
        if shipment.is_paid:
            return Response({"detail" : "This shipment is already paid."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = pay_with_wallet(shipment, request.user)
        except ValueError as e:
            return Response({"detail" : str(e)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.refresh_from_db()

        return Response({
            "detail" : "Payment successful.",
            "new_balance" : str(request.user.wallet_balance),
            "payment" : PaymentSerializer(payment).data,
        })



class WalletSummaryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        unpaid = Shipment.objects.filter(sender=user, is_paid=False).exclude(status__in=['cancelled', 'returned']).order_by('created_at')
        unpaid_list = [
            {
                "id" : str(s.id),
                "shipment_code" : s.shipment_code,
                "receiver_name" : s.receiever_name,
                "receiver_city" : s.receiver_city,
                "total_price" : str(s.total_price)
            } for s in unpaid

        ]
        return Response({
            "wallet_balance" : str(user.wallet_balance),
            "unpaid_shipments" : unpaid_list
        })


class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(user=self.request.user).order_by("-created_at")

class InitiatePaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        shipment_id = request.data.get("shipment_id")
        shipment = get_object_or_404(Shipment, id=shipment_id, sender=request.user)

        if shipment.is_paid:
            return Response({"detail" : "Shipment already paid."}, status=status.HTTP_400_BAD_REQUEST)

        data = initialize_paystack_payment(shipment, request.user)
        return Response(data)

class VerifyPaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reference = request.query_params.get("reference")
        if not reference:
            return Response({"detail" : "reference is required."}, status=status.HTTP_400_BAD_REQUEST)
        payment = verify_paystack_payment(reference)
        return Response(PaymentSerializer(payment).data)



