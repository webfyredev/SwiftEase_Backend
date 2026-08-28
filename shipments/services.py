import io
from reportlab.lib.pagesizes import A6
from reportlab.pdfgen import canvas as rl_canvas
import qrcode
import requests
from .models import *
from django.conf import settings
from notifications.models import *
from django.core.mail import send_mail

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
    c.rect(0, h -50, w, 50, fill=1, stroke=0)
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