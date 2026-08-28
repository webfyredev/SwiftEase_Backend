from django.db import models
from accounts.models import User
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
