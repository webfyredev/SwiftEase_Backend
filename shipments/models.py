from django.db import models
from django.utils import timezone
import uuid
from accounts.models import User
from fleet.models import *
import random
import string


def generate_tracking_code():
    letter = random.choice(string.ascii_uppercase)
    numbers = "".join(random.choices(string.digits, k=9))
    return letter + numbers

def generate_short_id(prefix="", length=8):
    chars = string.ascii_uppercase + string.digits
    return prefix + "".join(random.choices(chars, k=length))


class ServiceType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days_min = models.PositiveSmallIntegerField(default=1)
    estimated_days_max = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Shipment(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("dispatched", "Dispatched"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned")
    ]
    PAYMENT_METHODS = [
        ("online", "Online (Paystack)"),
        ("wallet", "Wallet"),
        ("cod", "Cash on Delivery"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment_code = models.CharField(max_length=12, unique=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sent_shipments')
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    sender_name = models.CharField(max_length=150)
    sender_phone = models.CharField(max_length=20)
    sender_address = models.TextField()
    sender_city = models.CharField(max_length=100)
    sender_state = models.CharField(max_length=100)

    receiver_name = models.CharField(max_length=150)
    receiver_phone = models.CharField(max_length=20)
    receiver_address = models.TextField()
    receiver_city = models.CharField(max_length=100)
    receiver_state = models.CharField(max_length=100)

    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    length_cm = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    width_cm = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    height_cm = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_fragile = models.BooleanField(default=False)
    declared_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    quoted_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    payment_method = models.CharField(max_length=20, choices = PAYMENT_METHODS, default='online')
    is_paid = models.BooleanField(default=False)

    assigned_driver = models.ForeignKey(DriverProfile, on_delete=models.SET_NULL, null=True, blank=True)
    origin_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.shipment_code:
            code = generate_short_id("SW", 8)
            while Shipment.objects.filter(shipment_code=code).exists():
                code = generate_short_id("SW", 8)
            self.shipment_code = code
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Shipment {self.shipment_code}"


class TrackingEvent(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("in_transit", "In Transit"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("held", "Held"),
        ("returned", "Returned"),
    ]

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="tracking_events")
    tracking_code = models.CharField(max_length=10, unique=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default='pending')
    location = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            code = generate_tracking_code()
            while TrackingEvent.objects.filter(tracking_code=code).exists():
                code = generate_tracking_code()
            self.tracking_code = code
        
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ["-timestamp"]
    
    def __str__(self):
        return f"{self.shipment.shipment_code} - {self.status} @ {self.location}"

class PickUpSlot(models.Model):
    STATUS = [
        ("available", "Available"),
        ("booked", "Booked"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled")
    ]
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='pickup_shipments', null=True, blank=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pickup_slots')
    slot_date = models.DateField()
    slot_time = models.TimeField()
    address = models.TextField()
    city = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS, default="booked")
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pickup {self.slot_date} { self.slot_time} -- {self.customer.full_name}"


class ProofOfDelivery(models.Model):
    shipment = models.OneToOneField(Shipment, on_delete=models.CASCADE, related_name="proof_of_delivery")
    signed_by = models.CharField(max_length=150)
    signature_image = models.ImageField(upload_to="signatures/", null=True, blank=True)
    delivery_photo = models.ImageField(upload_to="pod_photos/")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    delivered_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"POD of {self.shipment.shipment_code}"

class Review(models.Model):
    shipment = models.OneToOneField(Shipment, on_delete=models.CASCADE, related_name="review")
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} - {self.shipment.shipment_code}"
