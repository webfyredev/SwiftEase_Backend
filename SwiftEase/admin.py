from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    ordering = ['-date_joined']
    list_display = ["email", "full_name", "phone", "role", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["email", "full_name", "phone"]
    fieldsets = (
        (None, {"fields" : ("email", "password")}),
        ("Personal", {"fields" :("full_name", "phone", "avatar", "wallet_balance")}),
        ("Role & Permissions", {"fields" : ("role", "is_active", "is_staff", "is_superuser")}),
    )

    add_fieldsets = (
        (None, {"fields" : ("email", "full_name", "phone", "role", "password1", "password2")})
    )

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ["shipment_code", "sender", "receiver_name", "receiver_city", "status", "total_price", "is_paid"]
    list_filter = ["status", "is_paid", "service_type"]
    search_fields = ["shipment_code", "sender__email", "receiver_name", "receiver_phone"]
    readonly_fields = ["shipment_code", "created_at", "updated_at"]

@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display = ["tracking_code", "shipment", "status", "location", "timestamp"]
    list_filter = ["status"]
    search_fields = ["tracking_code", "shipment__shipment_code"]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["reference", "shipment", "user", "amount", "status", "paid_at"]
    list_filter = ["status"]
    search_fields = ["reference", "user__email"]

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["ticket_no", "user", "category", "subject", "status", "created_at"]
    list_filter = ["status", "category"]
    search_fields = ["ticket_no", "user__email", "subject"]


admin.site.register(Address)
admin.site.register(ServiceType)
admin.site.register(Branch)
admin.site.register(Vehicle)
admin.site.register(DriverProfile)
admin.site.register(PickUpSlot)
admin.site.register(WalletTransaction)
admin.site.register(ProofOfDelivery)
admin.site.register(Review)
admin.site.register(TicketReply)
admin.site.register(Notification)
