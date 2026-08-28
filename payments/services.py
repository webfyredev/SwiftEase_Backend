from shipments.models import Shipment, TrackingEvent
from shipments.services import send_in_app_notification, send_email_notification
from accounts.models import User
import uuid
from django.conf import settings
import requests
from .models import *
from django.utils import timezone

PAYSTACK_BASE = "https://api.paystack.co"
PAYSTACK_HEADERS = lambda : {
    "Authorization" : f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    "Content-Type" : "application/json"
}

def initialize_paystack_payment(shipment : Shipment, user : User) -> dict:
    reference = f"SW-{uuid.uuid4().hex[:12].upper()}"
    amount_kobo = int(float(shipment.total_price) * 100)

    payload = {
        "email" : user.email,
        "amount" : amount_kobo,
        "reference" : reference,
        "metadata" : {
            "shipment_code" : shipment.shipment_code,
            "user_id" : str(user.id)
        },
        "callback_url" : f"{settings.FRONTEND_URL}/payment/callback",
    }
    response = requests.post(
        f"{PAYSTACK_BASE}/transaction/initialize",
        json=payload,
        headers=PAYSTACK_HEADERS(),
        timeout=15
    )

    response.raise_for_status()
    data = response.json()

    Payment.objects.create(
        shipment = shipment,
        user=user,
        amount = shipment.total_price,
        reference = reference,
        status="pending"
    )

    return data["data"]

def verify_paystack_payment(reference:str) -> dict:
    response = requests.get(
        f"{PAYSTACK_BASE}/transaction/verify/{reference}",
        headers=PAYSTACK_HEADERS(),
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()["data"]

    payment = Payment.objects.get(reference=reference)
    if data["status"] == "success":
        payment.status = "success"
        payment.gateway_response = str(data)
        payment.paid_at = timezone.now()
        payment.save()

        shipment = payment.shipment
        shipment.is_paid  = True
        shipment.status = "confirmed"
        shipment.save()

        TrackingEvent.objects.create(
            shipment = shipment,
            status = "pending",
            location = shipment.sender_city,
            description = "Payment confirmed. Shipment is being processed"

        )

        send_in_app_notification(
            user = payment.user,
            title = "Payment Confirmed",
            message = f"Your shipment {shipment.shipment_code}",
            notif_type = "payment"
        )

        send_email_notification(
            to=payment.user.email,
            subject = f"SwiftEase - Shipment {shipment.shipment_code} Confirmed",
            body = (
                f"Hi {payment.user.full_name}, \n\n"
                f"Pyament of #{payment.amount} received. \n"
                f"Tracking code: {shipment.shipment_code} \n\n"
                "Thank you fo choosing SwiftEase!"
            )
        )
    else:
        payment.status = "failed"
        payment.save()
    
    return payment

def credit_wallet(user : User, amount : float, description : str) -> WalletTransaction:
    user.wallet_balance +=amount
    user.save(update_fields=["wallet_balance"])
    return WalletTransaction.objects.create(
        user = user,
        amount = amount,
        txn_type="credit",
        description = description,
        balance_after = user.wallet_balance

    )

def debit_wallet(user : User, amount : float, description : str) -> WalletTransaction:
    if float(user.wallet_balance) < amount:
        raise ValueError("Insufficient wallet balance.")
    user.wallet_balance -=amount
    user.save(update_fields=["wallet_balance"])
    return WalletTransaction.objects.create(
        user=user,
        amount=amount,
        txn_type="debit",
        description = description,
        balance_after = user.wallet_balance
    )

def pay_with_wallet (shipment : Shipment, user:User) -> Payment:
    txn = debit_wallet(user, float(shipment.total_price), f"Shipment {shipment.shipment_code}")
    payment = Payment.objects.create(
        shipment = shipment,
        user = user,
        amount = shipment.total_price,
        reference = f"WALLET-{uuid.uuid4().hex[:10].upper()}",
        status = "success",
        paid_at = timezone.now(),
        gateway_response = f"Wallet debit txn {txn.id}",
    )
    shipment.is_paid = True
    shipment.status = "confirmed"
    shipment.save()
    return payment
