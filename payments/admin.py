from django.contrib import admin
from .models import Payment, WalletTransaction
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ["reference", "shipment", "user", "amount", "status", "paid_at"]
    list_filter   = ["status"]
    search_fields = ["reference", "user__email"]

admin.site.register(WalletTransaction)
