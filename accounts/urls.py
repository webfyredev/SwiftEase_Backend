from django.urls import path
from .views import *
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, TokenBlacklistView)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name='register'),
    path("auth/login/", TokenObtainPairView.as_view(), name='login'),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name='refresh'),
    path("auth/logout/", TokenBlacklistView.as_view(), name='logout'),
    path("auth/profile/", ProfileView.as_view(), name="profile"),
    path("auth/avatar/", AvatarUploadView.as_view(), name='avatar-upload'),
    path("auth/change-password/", ChangePasswordView.as_view(), name='reset-password'),

    # Addresses --------------------------------------------------------------

    path("addresses/", AddressListCreateView.as_view(), name='address-list'),
    path("addresses/<int:pk>/", AddressDetailView.as_view(), name='address-detail'),
    
]