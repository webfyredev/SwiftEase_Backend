from django.contrib import admin
from .models import *
@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display   = ["shipment_code", "sender", "receiver_name", "receiver_city", "status", "total_price", "is_paid"]
    list_filter    = ["status", "is_paid", "service_type"]
    search_fields  = ["shipment_code", "sender__email", "receiver_name", "receiver_phone"]
    readonly_fields = ["shipment_code", "created_at", "updated_at"]



@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display  = ["tracking_code", "shipment", "status", "location", "timestamp"]
    list_filter   = ["status"]
    search_fields = ["tracking_code", "shipment__shipment_code"]


admin.site.register(ServiceType)
admin.site.register(PickUpSlot)
admin.site.register(ProofOfDelivery)
admin.site.register(Review)



