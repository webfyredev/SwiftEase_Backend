import random
import string
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

def generate_tracking_code():
    letter = random.choice(string.ascii_uppercase)
    numbers = "".join(random.choices(string.digits, k=9))
    return letter + numbers

def generate_short_id(prefix="", length=8):
    chars = string.ascii_uppercase + string.digits
    return prefix + "".join(random.choices(chars, k=length))

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password, **extra):
        extra.setdefault("role", "admin")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ("customer", "Customer"),
        ("driver", "Driver"),
        ("staff", "Staff"),
        ("admin", "Admin"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default="customer")
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'User'
    
    def __str__(self):
        return f'{self.full_name} ({self.email})'

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=60, default="Home") # "Home", "Office.."
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Nigeria")
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.label} - {self.street} - {self.city}"

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


class Branch(models.Model):
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.city}"


class Vehicle(models.Model):
    TYPE_CHOICES = [
        ("bike", "Bike"),
        ("van", "Van"),
        ("truck", "Truck"),
        ("car", "Car")
    ]
    plate_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    model = models.CharField(max_length=100)
    capacity_kg = models.DecimalField(max_digits=8, decimal_places=2)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, related_name='vehicles')
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.plate_number} ({self.vehicle_type})"

class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="driver_profile")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True,  blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    license_no = models.CharField(max_length=50)
    is_on_duty = models.BooleanField(default=False)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_long = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)

    def __str__(self):
        return f"Driver: {self.user.full_name}"

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


class Payment(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, related_name="payments")
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    gateway_response = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.reference} - {self.amount} ({self.status})"


class WalletTransaction(models.Model):
    TYPE = [
        ("credit", "Credit"),
        ("debit", "Debit")
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wallet_transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    txn_type = models.CharField(max_length=10, choices=TYPE)
    description = models.CharField(max_length=255)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.txn_type} - {self.amount} - {self.user.email}"


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

class SupportTicket(models.Model):
    STATUS = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed")
    ]

    CATEGORY = [
        ("delay", "Delay"),
        ("damage", "Damage"),
        ("missing", "Missing"),
        ("payment", "Payment"),
        ("other", "Other")
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_no = models.CharField(max_length=12, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets")
    shipment = models.ForeignKey(Shipment, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default="open")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tickets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.ticket_no:
            self.ticket_no = generate_short_id("TKT", 6)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"[{self.ticket_no}] {self.subject}"

class TicketReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="ticket_replies")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.author.full_name} on {self.ticket.ticket_no}"

class Notification(models.Model):
    TYPE = [
        ("shipment", "Shipment"),
        ("payment", "Payment"),
        ("promo", "Promo"),
        ("system", "System")
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notif_type = models.CharField(max_length=20, choices=TYPE, default="system")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
