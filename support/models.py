import uuid
from accounts.models import User
from shipments.models import Shipment, generate_short_id
from django.db import models

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

