from rest_framework import views, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from shipments.models import Shipment, TrackingEvent, ProofOfDelivery
from shipments.serializers import ShipmentListSerializer, ShipmentDetailsSerializer
from fleet.models import DriverProfile
from accounts.permissions import IsDriver
from notifications.models import Notification


class DriverDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]
    def get(self, request):
        user = request.user
        profile = user.driver_profile
        today = timezone.now().date()

        assigned = Shipment.objects.filter(assigned_driver=profile).select_related('service_type', 'sender').prefetch_related('tracking_events').order_by("-created_at")

        today_shipments = assigned.filter(created_at__date=today)

        total_assigned = today_shipments.count()
        completed = today_shipments.filter(status="delivered").count()
        pending = today_shipments.filter(status__in=['confirmed', 'processing', 'dispatched']).count()

        def serialize_shipment(s):
            latest_event = s.tracking_events.first()
            return{
                "id" : str(s.id),
                "shipment_code" : s.shipment_code,
                "status" : s.status,
                "service" : s.service_type.name,
                "receiver_name" : s.receiver_name,
                "receiver_phone" : s.receiver_phone,
                "receiver_address" : s.receiver_address,
                "receiver_city" : s.receiver_city,
                "receiver_state" : s.receiver_state,
                "sender_name" : s.sender_name,
                "sender_phone" : s.sender_phone,
                "sender_address" : s.sender_address,
                "sender_city" : s.sender_city,
                "sender_state" : s.sender_state,
                "weight_kg" : s.weight_kg,
                "is_fragile" : s.is_fragile,
                "description" : s.description,
                "latest_status" : latest_event
            }

        return Response({
            "driver" : {
                "full_name" : user.full_name,
                "email" : user.email,
                "phone" : user.phone,
                "role" : user.role,
                "avatar" : request.build_absolute_uri(user.avatar.url) if user.avatar else None,
                "rating" : str(profile.rating),
                "is_on_duty" : profile.is_on_duty,
                "license_no" : profile.license_no,
                "date_joined" : user.date_joined.strftime('%b %d %Y'),
            },
            "vehicle" : {
                "plate_number" : profile.vehicle.plate_number if profile.vehicle else None,
                "vehicle_type" : profile.vehicle.vehicle_type if profile.vehicle else None,
                "model" : profile.vehicle.model if profile.vehicle else None,
                "capacity_kg" : str(profile.vehicle.capacity_kg) if profile.vehicle else None,
            } if profile.vehicle else None,
            "branch" : {
                "name" : profile.branch.name if profile.branch else None,
                "city" : profile.branch.city if profile.branch else None,
                "address" : profile.branch.address if profile.branch else None,
            } if profile.branch else None,
            "stats" : {
                "total_assigned" : total_assigned,
                "completed" : completed,
                "pending" : pending,
            },
            "today_shipments" : [serialize_shipment(s) for s in today_shipments]
        })


class ToggleDutyView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        profile = request.user.driver_profile
        is_on_duty = request.data.get('is_on_duty')
        profile.is_on_duty = bool(is_on_duty)

        profile.save(update_fields=["is_on_duty"])
        return Response({
            "detail" : "Duty status updated",
            "is_on_duty" : profile.is_on_duty
        })


class DriverShipmentsView(generics.ListAPIView):
    permission_classes = [IsDriver]

    def get(self, request):
        profile = request.user.driver_profile
        status_tab = request.data.get('tab', 'all')
        qs = Shipment.objects.filter(assigned_driver=profile).select_related('service_type').prefetch_related('tracking_events').order_by("-created_at")

        if status_tab == 'active':
            qs = qs.filter(status__in=['confirmed', 'processing', 'dispatched'])
        elif status_tab == 'completed':
            qs = qs.filter(status='delivered')

        def serialize(s):
            return{
                "id" : s.id,
                "shipment_code" : s.shipment_code,
                "status" : s.status,
                "service" : s.service_type.name,
                "receiver_name" : s.receiver_name,
                "receiver_city" : s.receiver_city,
                "receiver_state" : s.receiver_state,
                "weight_kg" : s.weight_kg,
                "is_fragile" : s.is_fragile,
                "created_at" : s.created_at,
            }

        return Response([serialize(s) for s in qs])


class DriverShipmentDetailView(APIView):
    permission_classes = [IsDriver]

    def get(self, request, pk):
        profile = request.user.driver_profile
        shipment = get_object_or_404(Shipment, pk=pk, assigned_driver=profile)
        events = TrackingEvent.objects.filter(shipment=shipment).order_by("timestamp")

        return Response({
            "id" : str(shipment.id),
            "shipment_code" : shipment.shipment_code,
            "status" : shipment.status,
            "service" : shipment.service_type.name,
            "weight_kg" : shipment.weight_kg,
            "is_fragile" : shipment.is_fragile,
            "description" : shipment.description,
            "estimated_delivery" : shipment.estimated_delivery,
            "sender_name" : shipment.sender_name,
            "sender_phone" : shipment.sender_phone,
            "sender_address" : shipment.sender_address,
            "sender_city" : shipment.sender_city,
            "sender_state" : shipment.sender_state,

            "receiver_name" : shipment.receiver_name,
            "receiver_phone" : shipment.receiver_phone,
            "receiver_address" : shipment.receiver_address,
            "receiver_city" : shipment.receiver_city,
            "receiver_state" : shipment.receiver_state,

            "events" : [
                {
                    "status" : e.status,
                    "location" : e.location,
                    "description" : e.description,
                    "timestamp" : e.timestamp
                } for e in events
            ],
            "has_pod" : hasattr(shipment, "proof_of_delivery"),
        })


class UpdateShipmentStatusView(APIView):
    permission_classes = [IsDriver]

    def post(self, request, pk):
        profile = request.user.driver_profile
        shipment = get_object_or_404(Shipment, pk=pk, assigned_driver=profile)
        action = request.data.get('action')
        ACTION_MAP = {
            "picked_up" : ("in_tramsit", "dispatched", "Package picked up from sender."),
            "out_of_delivery" : ("out_of_delivery", 'dispatched', "Package is out for delivery"),

        }

        if action not in ACTION_MAP:
            return Response({"detail" : "Invalid action. Use picked_up or out_of_delivery"}, status=status.HTTP_400_BAD_REQUEST)

        event_status, shipment_status, description = ACTION_MAP

        TrackingEvent.objects.create(
            shipment=shipment,
            status=event_status,
            location = f"{shipment.sender_city if action == 'picked_up' else shipment.receiver_city}",
            description = description,
            created_by = request.user
        )

        shipment.status = shipment_status
        shipment.save(update_fields=['status'])

        Notification.objects.create(
            user = shipment.sender,
            title = f"Shipment Update - {shipment.shipment_code}",
            message = description,
            notif_type = "shipment"
        )

        return Response({"detail" : "status updated", "status" : shipment.status})


class SubmitProofOfDeliveryView(APIView):
    permission_classes = [IsDriver]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        profile = request.user.driver_profile
        shipment = get_object_or_404(Shipment, pk=pk, assigned_driver=profile)

        if hasattr(shipment, 'proof_of_delivery'):
            return Response({"detail" : "Proof of delivery already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        signed_by = request.data.get('signed_by', "").strip()
        delivery_photo = request.FILES.get('delivery_photo')
        signature_img = request.FILES.get('signature_image')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        notes  = request.data.get('notes', '')

        if not signed_by:
            return Response({"detail" : "Signed_by is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not delivery_photo:
            return Response({"detail" : "Delivery photo is required."}, status=status.HTTP_400_BAD_REQUEST,)


        pod = ProofOfDelivery.objects.create(
            shipment=shipment,
            signed_by=signed_by,
            delivery_photo = delivery_photo,
            signature_image= signature_img,
            latitude = latitude or None,
            longitude = longitude or None,
            notes = notes,
            created_by = request.user
        )
        shipment.status = "delivered"
        shipment.save(update_fields=['status'])

        TrackingEvent.objects.create(
            shipment = shipment,
            status="delivered",
            location = shipment.receiver_city,
            description = f"Delivered and signed bg {signed_by}.",
            created_by = request.user,
        )

        Notification.objects.create(
            user = shipment.sender,
            title = f"Delivered - {shipment.shipment_code}",
            message = f"Your shipment has been delivered and signed by {signed_by}",
            notif_type = "shipment"
        )


class DriverLocationUpdateView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        profile = request.user.driver_profile
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')

        if lat is None or lng is None:
            return Response({"detail" : "Latitude and longitude are required"}, status=status.HTTP_400_BAD_REQUEST)

        profile.current_lat = lat
        profile.current_lng = lng
        profile.last_location_update = timezone.now()
        profile.save(update_fields=['current_lat', 'current_lng', 'last_location_update'])

        return Response({
            "detail" : "Location updated.",
            "latitude" : lat,
            "longitude" : lng,
            "updated_at" : profile.last_location_update,
        })
