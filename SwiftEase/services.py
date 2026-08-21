import io
import uuid
import requests
import qrcode

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas as rl_canvas
from .models import *


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
            loading = shipment.sender_city,
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
                f"Pyament of #{payment.amount} received. \n",
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
    shipment_status = "confirmed"
    shipment.save()
    return payment

def send_in_app_notification(user:User, title:str, message : str, notif_type:str = "system"):
    return Notification.objects.create(
        user=user, title=title, message=message, notif_type=notif_type,
    )

def send_email_notification(to:str, subject:str, body:str):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)
    except Exception:
        pass

def send_sms_notification(phone:str, message:str):
    if not settings.TERMII_API_KEY:
        return
    try:
        requests.post(
            "https://api.ng.termii.com/api/sms/send",
            json={
                "to" : phone,
                "from" : settings.TERMII_SENDER_ID,
                "sms" : message,
                "type" : "plain",
                "channel" : "generic",
                "api_key" : settings.TERMII_API_KEY
            },
            timeout=10
        )
    except Exception:
        pass

def notify_tracking_update(shipment:Shipment, event:TrackingEvent):
    message = f"Update on {shipment.shipment_code} : {event.get_status_display()} at {event.location}."
    send_in_app_notification(shipment.sender, f"Shipment Update - {event.get_status_display()}", message, "shipment")
    send_email_notification(shipment.sender.email, f"SwiftEase - {shipment.shipment_code} Update", message)
    if shipment.sender.phone:
        send_sms_notification(shipment.sender.phone, message)


def generate_parcel_label_pdf(shipment: Shipment) -> bytes:
    buffer = io.BytesIO()
    c = rl_canvas.Canvas(buffer, pagesize=A6)
    w, h = A6

    qr_data = f"https://swiftease-backend.onrender.com/track/{shipment.shipment_code}"
    qr_img = qrcode.make(qr_data)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    c.setFillColorRGB(0.07, 0.44, 0.88)
    c.react(0, h -50, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w /2, h - 32, "SWIFTEASE")
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 44, "Fast. Reliable. Delivered.")

    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(qr_buf), w - 105, h - 155, 95, 95)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(15, h - 70, shipment.shipment_code)
    c.setFont("Helvetica", 9)
    c.drawString(15, h - 84, f"Service: {shipment.service_type}")

    c.setFont("Helvetica-Bold", 9)
    c.drawString(15, h - 105, "FROM")
    c.setFont("Helvetica", 9)
    c.drawString(15, h - 118, shipment.sender_name)
    c.drawString(15, h - 130, shipment.sender_address[:45])
    c.drawString(15, h - 142, f"{shipment.sender_city}, {shipment.sender_state}")
    c.drawString(15, h - 154, shipment.sender_phone)

    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(15, h - 165, w - 15, h - 165)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(15, h - 180, "DELIVER TO")
    c.setFont("Helvetica", 10)
    c.drawString(15, h - 195, shipment.receiver_name)
    c.drawString(15, h - 210, shipment.receiver_address[:45])
    c.drawString(15, h - 225, f"{shipment.receiver_city}, {shipment.receiver_state}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15, h - 245, shipment.receiver_phone)

    c.setFont("Helvetica", 8)
    c.drawString(15, h - 265, f"Weight: {shipment.weight_kg}")
    if shipment.is_fragile:
        c.setFillColorRGB(0.9, 0.1, 0.1)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(15, h - 278, "FRAGILE - HANDLE WITH CARE")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def calculate_rate(service, weight_kg: float, distance_km : float, declared_value: float =0) -> dict:
    base = float(service.base_price)
    w_charge = float(service.price_per_kg) * weight_kg
    d_charge = float(service.price_per_km) * distance_km
    insurance = round(declared_value * 0.01, 2)
    total = base + w_charge + d_charge + insurance

    return {
        "service_name" : service.name,
        "base_price" : round(base, 2),
        "weight_charge" : round(w_charge, 2),
        "distance_charge" : round(d_charge, 2),
        "insurance_fee" : insurance,
        "total" : round(total, 2),
        "estimated_days" : f"{service.estimated_days_min} - {service.estimated_days_max} business day(s)"

    }