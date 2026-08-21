from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsAdminOrStaff(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ("admin", "staff")


class IsDriver(BasePermission):
    def has_permission(self, request, view):
        return(
            request.user.is_authenticated and request.user.role == "driver" and hasattr(request.user, "driver_profile")
        )

class IsOwnerOrAdminOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ("admin", "staff"):
            return True
        return getattr(obj, "sender_id", None) == request.user.id