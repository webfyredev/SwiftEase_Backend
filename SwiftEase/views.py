from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework import generics, permissions, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *
from .serializers import *
from .services import *
from .permissions import *
from django.shortcuts import get_object_or_404

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

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class ChangePasswordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request" : request})
        serializers.is_valid(raise_exception=True)
        serializers.save()
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
        return super().get_queryset()
    
class ServiceTypeListView(generics.ListAPIView):
    serializer_class = ServiceTypeSerializer
    permission_classes = [permissions.AllowAny]
    queryset = ServiceType.objects.filter(is_active=True)

class RateCalculatorView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RateQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        result = calculate_rate(
            service = d["service_type_id"],
            weight_kg= float(d["weight_kg"]),
            distance_km= float(d["distance_km"]),
            declared_value= float(d["declared_value"]),
        )

        return Response(RateResultSerializer(result).data)

class ShipmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ShipmentDetailsSerializer
        return ShipmentListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ("admin", "staff"):
            qs = Shipment.objects.all()
        else:
            qs = Shipment.objects.filter(sender=user)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related("service_type", "sender").prefetch_related("tracking_events")

    def get_serializer_context(self):
        ctx =  super().get_serializer_context()
        ctx["distance_km"] = float(self.request.data.get("distance_km", 0))

class ShipmentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ShipmentDetailsSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrStaff]

    def get_queryset(self):
        return Shipment.objects.select_related("service_type", "sender").prefetch_related("tracking_events")

class PublicTrackView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, code):
        shipment = get_object_or_404(Shipment, shipment_code=code.upper())
        events = TrackingEvent.objects.filter(shipment=shipment)
        return Response({
            "shipment_code" : shipment.shipment_code,
            "status" : shipment.status,
            "service" : shipment.service_type.name,
            "sender_city" : shipment.sender_city,
            "reciever_name" : shipment.receiver_name,
            "reciever_city" : shipment.receiver_city,
            "reciever_state" : shipment.receiver_state,
            "estimated_delivery" : shipment.estimated_delivery,
            "events" : TrackingEventsSerializer(events, many=True).data
            if "TrackingEventsSerializer" in dir() else [],
        })


class AddTrackingEventView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def create(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        from .serializers import TrackingEventsSerializer
        serializer = TrackingEventsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(shipment=shipment, created_by=request.user)
        status_map = {
            "in_transit" : "dispatched",
            "out_of_delivery" : "dispatched",
            "delivered" : "delivered",
            "returned" : "returned",
        }

        new_status = status_map.get(event.status)
        if new_status:
            shipment.status = new_status
            shipment.save(update_fields=["status"])

        notify_tracking_update(shipment, event)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ShipmentLabelView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        self.check_object_permissions(request, shipment)
        pdf_bytes = generate_parcel_label_pdf(shipment)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (f'attachment; filename="label_{shipment.shipment_code}.pdf"')
        return Response

class PickUpSlotListCreateView(generics.ListCreateAPIView):
    serializer_class = PickUpSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role in ("admin", "staff"):
            return PickUpSlot.objects.all()
        return PickUpSlot.objects.filter(customer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)


class PickUpSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PickUpSlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role in ("admin", "staff"):
            return PickUpSlot.objects.all()
        return PickUpSlot.objects.filter(customer=self.request.user)


class InitiatePaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        shipment_id = request.data.get("shipment_id")
        shipment = get_object_or_404(Shipment, id=shipment_id, sender=request.user)

        if shipment.is_paid:
            return Response({"detail" : "Shipment already paid."}, status=400)

        data = initialize_paystack_payment(shipment, request.user)
        return Response(data)

class VerifyPaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reference = request.query_params.get("reference")
        if not reference:
            return Response({"detail" : "reference is required."}, status=400)
        payment = verify_paystack_payment(reference)
        return Response(PaymentSerializer(payment).data)

class WalletTopUpView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WalletTopupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ref = serializer.validated_data["reference"]
        amount = float(serializer.validated_data["amount"])

        response = __import__("requests").get(
            f"https://api.paystack.co/transaction/verify/{ref}",
            headers={"Authorization" : f"Bearer {__import__('django.conf', formlist=['settings']).settings.PAYSTACK_SECRET_KEY}"},
            timeout=15,
        )

        data = response.json()["data"]
        if data["status"] != "success":
            return Response({"detail" : "Payment not successful"}, status=400)
        from .services import credit_wallet

        txn = credit_wallet(request.user, amount, f"Wallet top-up via Paystack ref {ref}")
        return Response(WalletTransactionSerializer(txn).data)

class WalletPayView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        shipment = get_object_or_404(Shipment, id=request.data.get("shipment_id"), sender=request.user)
        try:
            payment = pay_with_wallet(shipment, request.user)
        except ValueError as e:
            return Response({"detail" : str(e)}, status=400)
        return Response(PaymentSerializer(payment).data)

class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(user=self.request.user)


class ProofOfDeliveryCreateView(generics.CreateAPIView):
    serializer_class = ProofOfDeliverySerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def perform_create(self, serializer):
        shipment = get_object_or_404(Shipment, pk=self.kwargs["pk"])
        pod = serializer.save(shipment=shipment, created_by=self.request.user)

        shipment.status = "delivered"
        shipment.save(update_fields=["status"])
        event = TrackingEvent.objects.create(shipment=shipment, status="delivered", location=shipment.receiver_city, description=f"Delivered and signed by {pod.signed_by}.", created_at=self.request.user)
        notify_tracking_update(shipment, event)


class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        shipment = get_object_or_404(Shipment, pk=self.kwargs["pk"], sender=self.request.user, status="delivered")
        serializer.save(customer=self.request.user, shipment=shipment)


class SupportTicketListCreateView(generics.ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role in ("admin", "staff"):
            return SupportTicket.objects.all().prefetch_related("replies")
        return SupportTicket.objects.filter(user=self.request.user).prefetch_related("replies")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketReplyView(generics.CreateAPIView):
    serializer_class = TicketReplySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        ticket = get_object_or_404(SupportTicket, pk=self.kwargs["pk"])
        serializer.save(ticket=ticket, author=self.request.user)

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class MarkNotificationReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return Response({"detail" : "Marked as read"})

class MarkAllReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail" : "All notification marked as read."})

class DriverLocationUpdateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request):
        from django.utils import timezone as tz
        profile = request.user.driver_profile
        profile.current_lat = request.data.get("latitude")
        profile.current_lng = request.data.get("longitude")
        profile.last_location_update = tz.now()
        profile.save(update_fields=["current_lat", "current_lng", "last_location_update"])
        return Response({"detail" : "Location updated."})

class DriverShipmentsView(generics.ListAPIView):
    serializer_class = ShipmentListSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def get_queryset(self):
        return Shipment.objects.filter(assigned_driver=self.request.user.driver_profile, status__in=["confirmed", "processing", "dispatched"],)

class AdminDashboardView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        from django.db.models import Count, Sum
        from django.utils import timezone as tz
        today = tz.now().date()

        shipments_today = Shipment.objects.filter(created_at__date=today)
        total_revenue = Payment.objects.filter(status="success").aggregate(t=Sum("amount"))["t"] or 0

        return Response({
            "total_shipments" : Shipment.objects.count(),
            "shipment_today" : shipments_today.count(),
            "pending_shipments" : Shipment.objects.filter(status__in=["confirmed", "processing"]).count(),
            "delivered_today" : Shipment.objects.filter(status="delivered", updated_at__date=today).count(),
            "total_revenue" : total_revenue,
            "open_tickets" : SupportTicket.objects.filter(status="open").count(),
            "active_drivers" : DriverProfile.objects.filter(is_on_duty = True).count(),

        })

class AdminShipmentListView(generics.ListAPIView):
    serializer_class = ShipmentListSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get_queryset(self):
        qs = Shipment.objects.all().select_related("service_type", "sender")
        s = self.request.query_params.get("status")
        if s:
            qs = qs.filter(status=s)
        return qs
