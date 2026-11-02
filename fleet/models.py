from django.db import models
from accounts.models import User

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

