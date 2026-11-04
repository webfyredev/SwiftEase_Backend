from rest_framework import generics, status, views, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum, Avg
from rest_framework.pagination import PageNumberPagination
 

from shipments.models import *
from payments.models import *
from fleet.models import *
from support.models import *
from notifications.models import *
from accounts.permissions import IsAdminOrStaff, IsAdmin
from accounts.serializers import UserSerializer
from shipments.serializers import ShipmentListSerializer, ShipmentDetailsSerializer

User = get_user_model()


class CustomPagination(PageNumberPagination):
    page_size =  20
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        today = timezone.now().date()
        week_start = today - timedelta(days=7)
        month_start = today.replace(day=1)
        total_shipments = Shipment.objects.count()
        shipments_today = Shipment.objects.filter(created_at__date=today).count()
        pending_action = Shipment.objects.filter(status__in=['confirmed', 'processing']).count()
        delivered_today = Shipment.objects.filter(updated_at__date=today, status='delivered').count()
        total_revenue = Payment.objects.filter(status='success').aggregate(t=Sum("amount"))['t'] or 0
        month_revenue = Payment.objects.filter(status='success', paid_at__date__gte=month_start).aggregate(t=Sum("amount"))['t'] or 0
        today_revenue = Payment.objects.filter(status="success", paid_at__date=today).aggregate(t=Sum("amount"))['t'] or 0
        open_tickets = SupportTicket.objects.filter(status='open').count()
        active_drivers = DriverProfile.objects.filter(is_on_duty=True).count()
        total_customers = User.objects.filter(role='customer').count()

        revenue_chart = []
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            rev = Payment.objects.filter(status="success", paid_at__date=day).aggregate(t=Sum("amount"))['t'] or 0
            revenue_chart.append({
                "date" : str(day),
                "revenue" : float(rev)
            })

        status_breakdown = list(Shipment.objects.values("status").annotate(count=Count("id")).order_by("-count"))
        recent_shipments = Shipment.objects.select_related('service_type', 'sender').order_by('-created_at')[:8]

        def ser_shipments(s):
            return {
                "id" : str(s.id),
                "shipment_code" : s.shipment_code,
                "sender_name" : s.sender_name,
                "receiver_name" : s.receiver_name,
                "receiver_city" : s.receiver_city,
                "service" : s.service_type.name,
                "status" : s.status,
                "total_price" : str(s.total_price),
                "is_paid" : s.is_paid,
                "created_at" : s.created_at
            }

        on_duty_drivers = DriverProfile.objects.filter(is_on_duty=True).select_related("user", 'vehicle')[:6]

        def ser_driver(d):
            return{
                "name" : d.user.full_name,
                "vehicle" : d.vehicle.plate_number if d.vehicle else "",
                "vehicle_type" : d.vehicle.vehicle_type if d.vehicle else "",
                "rating" : str(d.rating),
            }

        recent_tickets = SupportTicket.objects.filter(status__in=['open', 'in_progress']).select_related("user").order_by("-created_at")[:5]
        
        def ser_ticket(t):
            return {
                "id" : str(t.id),
                "ticket_no" : t.ticket_no,
                "user_name" : t.user.full_name,
                "subject" : t.subject,
                "category" : t.get_category_display(),
                "status" : t.status,
                "created_at" : t.created_at,
            }
        
        return Response({
            "res" : {
                "total_shipments" : total_shipments,
                "shipments_today" : shipments_today,
                "pending_action" : pending_action,
                "delivered_today" : delivered_today,
                "total_revenue" : float(total_revenue),
                "month_revenue" : float(month_revenue),
                "today_revenue" : float(today_revenue),
                "open_tickets" : open_tickets,
                "active_drivers" : active_drivers,
                "total_customers" : total_customers
            },
            "revenue_chart" : revenue_chart,
            "status_breakdown" : status_breakdown,
            "recent_shipments" : [ser_shipments(s) for s in recent_shipments],
            "active_drivers" : [ser_driver(d) for d in on_duty_drivers],
            "recent_tickets" : [ser_ticket(t) for t in recent_tickets],
        })


class AdminShipmentListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        qs = Shipment.objects.select_related('service_type', 'sender', 'assigned_driver__user').prefetch_related("tracking_events").order_by('-created_at')

        status = request.query_params.get('status')
        service = request.query_params.get('service')
        search = request.query_params.get('search')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        is_paid = request.query_params.get('is_paid')

        if status:
            qs = qs.filter(status=status)
        if service:
            qs = qs.filter(service_type_id=service)
        if is_paid:
            qs = qs.filter(is_paid=is_paid == "true")

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        if search:
            qs = qs.filter(Q(shipment_code__icontains=search)| Q(sender_name__icontains=search)| Q(receiver_name__icontains=search)|Q(receiver_city__icontains=search)|Q(sender_city__icontains=search))

        paginator = CustomPagination()
        paginated_qs = paginator.paginate_queryset(qs, request)

        def serialize(s):
            return{
                "id" : str(s.id),
                "shipment_code" : s.shipment_code,
                "sender_name" : s.sender_name,
                "receiver_name" : s.receiver_name,
                "receiver_city" : s.receiver_city,
                "receiver_state" : s.receiver_state,
                "service" : s.service_type.name,
                "weight_kg" : str(s.weight_kg),
                'total_price' : str(s.total_price),
                "status" : s.status,
                "is_paid" : s.is_paid,
                "payment_method" : s.payment_method,
                "driver" : s.assigned_driver.user.full_name if s.assigned_driver else None,
                "created_at" : s.created_at
            }
        return Response({
            "pagination" : {
                "count" : paginator.page.paginator.count,
                "next" : paginator.get_next_link(),
                "previous" : paginator.get_previous_link(),
                "current_page" : paginator.page.number,
                "total_pages" : paginator.page.paginator.num_pages,
            },
            "results" : [serialize(s) for s in paginated_qs]
        })

class AdminShipmentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get(self, request, pk):
        shp = get_object_or_404(
            Shipment.objects.select_related('service_type', 'sender', 'assigned_driver__user', 'origin_branch').prefetch_related("tracking_events", "payments"),
            pk=pk,
        )
        events = [
            {
                "status" : e.status,
                "location" : e.location,
                "description" : e.description,
                "timestamp" : e.timestamp,
                "created_by" : e.created_by.full_name if e.created_by else None
            } for e in shp.tracking_events.order_by('timestamp')
        ],
        payments = [
            {
                "reference" : p.reference,
                "amount" : str(p.amount),
                "status" : p.status,
                "method" : p.shipment.payment_method,
                "paid_at" : p.paid_at,
            } for p in shp.payments.all()
        ]
        return Response({
            "id" : str(shp.id),
            "shipment_code" : shp.shipment_code,
            "status" : shp.status,
            "service" : shp.service_type.name,
            "sender_name" : shp.sender_name,
            "sender_phone" : shp.sender_phone,
            "sender_address" : shp.sender_address,
            "sender_city" : shp.sender_city,
            "sender_state" : shp.sender_state,

            "receiver_name" : shp.receiver_name,
            "receiver_phone" : shp.receiver_phone,
            "receiver_address" : shp.receiver_address,
            "receiver_city" : shp.receiver_city,
            "receiver_state" : shp.receiver_state,


            "weight_kg" : shp.weight_kg,
            "is_fragile" : shp.is_fragile,
            "description" : shp.description,
            "declared_value" : str(shp.declared_value),
            "quoted_price" : str(shp.quoted_price),
            "insurance_fee" : str(shp.insurance_fee),
            "total_price" : str(shp.total_price),
            "is_paid" : shp.is_paid,
            "payment_method" : shp.payment_method,
            "estimated_delivery" : shp.estimated_delivery,
            "driver" : shp.assigned_driver.user.full_name if shp.assigned_driver else None,
            "driver_id" : shp.assigned_driver.id if shp.assigned_driver else None,
            "branch" : shp.origin_branch.name if shp.origin_branch else None,
            "notes" : shp.notes,
            "created_at" : shp.created_at,
            "tracking_events" : events,
            "payments" : payments
        })


class AdminUpdateShipmentStatusView(APIView):
    permission_classes  = [permissions.IsAuthenticated, IsAdminOrStaff]

    def patch(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        new_status = request.data.get('status')
        location = request.data.get('location', shipment.sender_city)
        description = request.data.get('description', '')

        VALID_STATUSES = [s[0] for s  in Shipment.STATUS]
        if new_status not in VALID_STATUSES:
            return Response({
                "detail" : f"Invalid status. Choose from: {VALID_STATUSES}",
                
            }, status=status.HTTP_400_BAD_REQUEST)


        EVENT_MAP = {
            "confirmed" : "pending",
            "processing" : "pending",
            "dispatched" : "in_transit",
            "delivered" : "delivered",
            "returned" : "returned",
        }

        event_status = EVENT_MAP.get(new_status, 'pending')

        TrackingEvent.objects.create(
            shipment = shipment,
            status= event_status,
            location = location,
            description = description or f"Status updtaed to {new_status}",
            created_by = request.user,
        )
        shipment.status = new_status
        shipment.save(update_fields=["status"])

        Notification.objects.create(
            user = shipment.sender,
            title = f"Shipment Update {shipment.shipment_code}",
            message = f"Your shipment status has been updated to {new_status}.",
            notif_type = "shipment",
        )

        return Response({"detail" : "Status updated", "status" : new_status})


class AdminAssignDriverView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def patch(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        driver_id = request.data.get('driver_id')

        if not driver_id:
            return Response({"detail" : "Driver id is required"}, status=status.HTTP_400_BAD_REQUEST)

        driver = get_object_or_404(DriverProfile, id=driver_id)

        shipment.assigned_driver = driver
        shipment.save(update_fields=['assigned_driver'])

        Notification.objects.create(
            user = driver.user,
            title = "New Delivery assigned",
            message = f"You have been assigned shipment {shipment.shipment_code} to {shipment.receiver_city}",
            notif_type = "shipment"
        )

        return Response({"detail" : "Driver assigned", "driver" : driver.user.full_name})



class AdminDriverListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        profiles = DriverProfile.objects.select_related('user', 'vehicle', 'branch').order_by('-user__date_joined')

        def serialize(d):
            delivered = Shipment.objects.filter(assigned_driver=d, status='delivered').count()
            return{
                "id" : d.id,
                "full_name" : d.user.full_name,
                "email" : d.user.email,
                "phone" : d.user.phone,
                "is_on_duty" : d.is_on_duty,
                "rating" : str(d.rating),
                "vehicle" : f"{d.vehicle.plate_number} ({d.vehicle.vehicle_type})" if d.vehicle else None,
                "branch" : d.branch.name,
                "deliveries" : delivered,
                "last_seen" : d.last_location_update,
            }

        return Response([serialize(d) for d in profiles]) 


class AdminTicketListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get(self, request):
        status = request.query_params.get('status')
        qs = SupportTicket.objects.select_related('user', 'shipment', 'assigned_to').prefetch_related('ticket_replies')

        if status:
            qs = qs.filter(status=status)

        paginator = CustomPagination()
        paginated_tk = paginator.paginate_queryset(qs, request)

        def serialize(t):
            return{
                "id" : str(t.id),
                "ticket_no" : t.ticket_no,
                "user_name" : t.user.full_name,
                "user_email" : t.user.email,
                "category" : t.get_category_display(),
                "subject" : t.subject,
                "status" : t.status,
                "assigned_to" : t.assigned_to.full_name if t.assigned_to else None,
                "reply_count" : t.ticket_replies.count(),
                "created_at" : t.created_at,
                "updated_at" : t.updated_at
            }
        return Response({
            "pagination" : {
                "count" : paginator.page.paginator.count,
                "previous" : paginator.get_previous_link(),
                "next" : paginator.get_next_link(),
                "current_page" : paginator.page.number,
                "total_page" : paginator.page.paginator.num_pages,
            },
            "ticket_data" : [serialize(t) for t in paginated_tk]
            
        })

class AdminTicketDetailView(APIView):
    permission_classes  = [permissions.IsAuthenticated, IsAdminOrStaff]

    def get(self, request, pk):
        ticket = get_object_or_404(SupportTicket.objects.select_related("user", 'shipment').prefetch_related("ticket_replies__author"), pk=pk)
        replies = [
            {
                "id" : r.id,
                "author_name" : r.author.full_name,
                "is_staff" : r.author.role in ("admin", "staff"),
                "message" : r.message,
                "created_at" : r.created_at
            } for r in ticket.ticket_replies.order_by('-created_at')
        ]

        return Response({
            "id" : str(ticket.id),
            "ticket_no" : ticket.ticket_no,
            "user_name" : ticket.user.full_name,
            "user_email" : ticket.user.email,
            "category" : ticket.get_category_display(),
            "subject" : ticket.subject,
            "description" : ticket.description,
            "status" : ticket.status,
            "shipment_code" : ticket.shipment.shipment_code if ticket.shipment else None,
            "replies" : replies,
            "created_at" : ticket.created_at
        })

class AdminTicketReplyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrStaff]

    def post(self, request, pk):
        ticket = get_object_or_404(SupportTicket, pk=pk)
        message = request.data.get('message', "").strip()

        if not message:
            return Response({"detail" : "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        reply = TicketReply.objects.create(
            ticket=ticket,
            author = request.user,
            message=message
        )
        if ticket.status == "open":
            ticket.status = "in_progress"
            ticket.save(update_fields=['status'])


        Notification.objects.create(
            user = request.user, 
            title = f"Reply on Ticket {ticket.ticket_no}",
            message = f"SwiftEase Supportreplied to your ticket: {ticket.subject}",
            notif_type ="system"
        )

        return Response({
            "id" : reply.id,
            "author_name" : reply.author.full_name, 
            "message" : reply.message,
            "created_at" : reply.created_at 
        }, status=status.HTTP_201_CREATED)


class AdminTicketUpdateStatusView(APIView):
    permission_classes=[permissions.IsAuthenticated, IsAdminOrStaff]

    def path(self, request, pk):
        ticket = get_object_or_404(SupportTicket, pk=pk)
        new_status = request.data.get('status')
        ticket.save(update_fields=['status'])
        return Response({"status" : ticket.status})