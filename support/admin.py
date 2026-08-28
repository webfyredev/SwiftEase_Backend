from django.contrib import admin
from .models import SupportTicket, TicketReply

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display  = ["ticket_no", "user", "category", "subject", "status", "created_at"]
    list_filter   = ["status", "category"]
    search_fields = ["ticket_no", "user__email", "subject"]


admin.site.register(TicketReply)

