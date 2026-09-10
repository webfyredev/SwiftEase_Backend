from django.shortcuts import render
from .models import *
from rest_framework import generics, permissions, views, status
from .serializers import *
from rest_framework.response import Response
from .services import *
from accounts.permissions import *
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from payments.models import Payment
from datetime import timedelta
from django.db.models import Count, Q, Sum
from payments.services import *


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

        return Response(result)
        # return Response(RateResultSerializer(result).data)

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
        return ctx

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shipment = serializer.save()
        if shipment.payment_method == "wallet":
            try:
                pay_with_wallet(shipment, request.user)
            except ValueError as e:
                return Response({**serializer.data, "warning" : str(e)}, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ShipmentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ShipmentDetailsSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrStaff]

    def get_queryset(self):
        return Shipment.objects.select_related("service_type", "sender", "assigned_driver", "origin_branch").prefetch_related("tracking_events")

class ShipmentLabelView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        self.check_object_permissions(request, shipment)
        pdf_bytes = generate_parcel_label_pdf(shipment)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="label_{shipment.shipment_code}.pdf"'
        return response

    
class PublicTrackView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, code):
        shipment = get_object_or_404(Shipment, shipment_code=code.strip().upper())
        events = TrackingEvent.objects.filter(shipment=shipment).order_by("timestamp")

        return Response({
            "shipment_code" : shipment.shipment_code,
            "status" : shipment.status,
            "service" : shipment.service_type.name,
            "sender_city" : shipment.sender_city,
            "receiver_name" : shipment.receiver_name,
            "receiver_city" : shipment.receiver_city,
            "receiver_state" : shipment.receiver_state,
            "weight_kg" : str(shipment.weight_kg),
            "is_fragile" : shipment.is_fragile,
            "description" : shipment.description,
            "estimated_delivery" : shipment.estimated_delivery,
            "created_at" : shipment.created_at,
            "events" : TrackingEventsSerializer(events, many=True).data
        })

class AuthenticatedTrackView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, code):
        if request.user.role in ("admin", "staff"):
            shipment = get_object_or_404(Shipment, shipment_code=code.strip().upper())
        else:
            shipment = get_object_or_404(Shipment, shipment_code=code.strip().upper(), sender=request.user)

        events = TrackingEvent.objects.filter(shipment=shipment).order_by("timestamp")

        return Response({
            "shipment_code" : shipment.shipment_code,
            "status" : shipment.status,
            "service" : shipment.service_type.name,
            "is_paid" : shipment.is_paid,
            "payment_method" : shipment.payment_method,
            "total_price" : str(shipment.total_price),
            "sender_name" : shipment.sender_name,
            "sender_city" : shipment.sender_city,
            "sender_state" : shipment.sender_state,
            "sender_phone" : shipment.sender_phone,
            "sender_address" : shipment.sender_address,
            "receiver_name" : shipment.receiver_name,
            "receiver_phone" : shipment.receiver_phone,
            "receiver_address" : shipment.receiver_address,
            "receiver_city" : shipment.receiver_city,
            "receiver_state" : shipment.receiver_state,
            "weight_kg" : str(shipment.weight_kg),
            "is_fragile" : shipment.is_fragile,
            "description" : shipment.description,
            "declared_value" : str(shipment.declared_value),
            "estimated_delivery" : shipment.estimated_delivery,
            "created_at" : shipment.created_at,
            "updated_at" : shipment.updated_at,
            "driver_name" : (shipment.assigned_driver.user.full_name if shipment.assigned_driver else None),
            "driver_phone" : (shipment.assigned_driver.user.phone if shipment.assigned_driver else None ),
            "events" : TrackingEventsSerializer(events, many=True).data
        })


class AddTrackingEventView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        serializer = TrackingEventsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(shipment=shipment, created_by=request.user)
        status_map = {
            "in_transit" : "dispatched",
            "out_for_delivery" : "dispatched",
            "delivered" : "delivered",
            "returned" : "returned",
        }

        new_status = status_map.get(event.status)
        if new_status:
            shipment.status = new_status
            shipment.save(update_fields=["status"])

        notify_tracking_update(shipment, event)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



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

class CustomerDashboardView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        user_shipments = Shipment.objects.filter(sender=user)
        total_shipments = user_shipments.count()
        delivered = user_shipments.filter(status='delivered').count()
        in_transit = user_shipments.filter(status__in=["confirmed", "processing", "dispatched"]).count()
        pending_payments = user_shipments.filter(is_paid=False).exclude(status__in=["cancelled", "returned"]).count()
        recent_shipments = user_shipments.select_related("service_type").prefetch_related('tracking_events').order_by("-created_at")[:5]
        today = timezone.now().date()
        chart_data = []
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            month_shipments = user_shipments.filter(created_at__date__gte=month_start, created_at__date__lte=month_end)
            month_revenue = Payment.objects.filter(user=user, status="success", created_at__gte=month_start, created_at__lte=month_end).aggregate(total=Sum("amount"))["total"] or 0
            chart_data.append({
                "month" : month_start.strftime("%b"),
                "shipments" : month_shipments.count(),
                "revenue" : float(month_revenue),
            })
        week_start = today - timedelta(days=today.weekday())
        week_data = []
        day_labels = ["Mon", "Tue", "Wed", "Thur", "Fri", "Sat", "Sun"]
        for i in range(7):
            day = week_start + timedelta(days=i)
            week_data.append({
                "day" : day_labels[i],
                "shipments" : user_shipments.filter(created_at__date=day).count(),
                "delivered" : user_shipments.filter(status="delivered", updated_at__date=day).count(),
            })

        return Response({
            "user" : {
                "full_name" : user.full_name,
                "email" : user.email,
                "wallet_balance" : float(user.wallet_balance),
                "avatar" : request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            },
            "stats" : {
                "total_shipments" : total_shipments,
                "in_transit" : in_transit,
                "delivered" : delivered,
                "pending_payment" : pending_payments
            },
            "chart" : {
                "monthly" : chart_data,
                "weekly" : week_data,

            },
            "recent_shipments" : ShipmentListSerializer(
                recent_shipments, many=True, context={"request" : request}
            ).data,
            
        }) 
