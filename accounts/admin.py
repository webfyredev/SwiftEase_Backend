from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering        = ["-date_joined"]
    list_display    = ["email", "full_name", "phone", "role", "is_active"]
    list_filter     = ["role", "is_active"]
    search_fields   = ["email", "full_name", "phone"]
    fieldsets       = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("full_name", "phone", "avatar", "wallet_balance")}),
        ("Role & Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets   = (
        (None, {"fields": ("email", "full_name", "phone", "role", "password1", "password2")}),
    )


admin.site.register(Address)

