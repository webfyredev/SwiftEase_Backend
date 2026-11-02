from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework import generics, permissions, status, views
# from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import *
from .serializers import *
from .permissions import *
import string
import secrets

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterUserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user" : UserSerializer(user).data,
            "refresh" : str(refresh),
            "access" : str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

class AdminCreateStaffView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        full_name = request.data.get('full_name', '').strip()
        phone = request.data.get('phone', '').strip()


        if not email or not full_name:
            return Response({"detail" : "Email and full name are required" }, status=status.HTTP_400_BAD_REQUEST)

        if User.objetcts.filter(email=email).exists():
            return Response({"detail" : "Email already existed"}, status=status.HTTP_400_BAD_REQUEST)
        
        alphabet = string.ascii_letters + string.digits + '!@#$'
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        user = User.objects.create(
            email=email,
            full_name=full_name,
            phone=phone,
            password=temp_password,
            role="staff"
        )

        return Response({"detail" : "Staff account created", "user" : UserSerializer(user).data, "temp_password" : temp_password, "note" : "Share this temporary password with the staff memeber. They should change it on first login"}, status=status.HTTP_201_CREATED)
class ChangePasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request" : request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail" : "Password updated successfully."})


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

class AvatarUploadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        avatar = request.FILES.get('avatar')
        if not avatar:
            return Response({
                "detail" : "No image file provided."
            }, status=status.HTTP_400_BAD_REQUEST,)

        if avatar.size > 5 * 1024 * 1024:
            return Response({"detail" : "Image must be smaller than 5MB."}, status=status.HTTP_400_BAD_REQUEST)

        if not avatar.content_type.startswith("image/"):
            return Response({"detail" : "File must be an image."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.avatar = avatar
        user.save(update_fields=["avatar"])

        return Response({"detail" : "Avatar updated", "avatar" : request.build_absolute_uri(user.avatar.url)})