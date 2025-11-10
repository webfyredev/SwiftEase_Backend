from django.db import models
import random
import string

def generate_tracking_code():
    letter = random.choice(string.ascii_uppercase)
    numbers = ''.join(random.choices(string.digits, k=9))
    return letter + numbers

class Tracking_Package(models.Model):
    STATUS = [
        ('Pending', 'Pending'),
        ('In Transit', 'In Transit'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Held', 'Held'),
        ('Returned', 'Returned'),
    ]
    tracking_code = models.CharField(max_length=10, unique=True, blank=True)
    sender_name = models.CharField(max_length=100)
    reciever_name = models.CharField(max_length=100)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    current_location = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=STATUS)
    estimated_delivery = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            new_code = generate_tracking_code()

            while Tracking_Package.objects.filter(tracking_code=new_code).exists():
                new_code = generate_tracking_code()
            self.tracking_code = new_code

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'Tracking Package - {self.tracking_code}'

class Contacts(models.Model):
    SERVICES = [
        ('Freight Transport', 'Freight Transport'),
        ('WareHousing', 'WareHousing'),
        ('E-commerce Delivery', 'E-commerce Delivery'),
        ('International Shipping', 'International Shipping'),
    ]
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    company_name = models.CharField(max_length=100)
    service = models.CharField(max_length=100, choices=SERVICES)
    message = models.TextField()

    def __str__(self):
        return f'Message from {self.full_name}'
    
    class Meta:
        verbose_name = 'Contacts'
        verbose_name_plural = 'Contacts'