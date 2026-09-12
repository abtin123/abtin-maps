from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.permissions import HasPermissionCode
from .models import Route, RouteStop, Visit, GPSTrack, Vehicle, DeliveryTrip, DeliveryStop, DeliveryAttempt
from .serializers import *
from .services import start_visit, finish_visit, start_trip, record_delivery

class DeliveryPermissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_map = {'list': 'delivery.view', 'retrieve': 'delivery.view', 'create': 'delivery.manage', 'update': 'delivery.manage', 'partial_update': 'delivery.manage', 'destroy': 'delivery.manage'}
    def get_permissions(self):
        self.required_permission = self.permission_map.get(self.action, 'delivery.view')
        return super().get_permissions()

class RouteViewSet(DeliveryPermissionViewSet):
    queryset = Route.objects.select_related('branch', 'zone', 'sales_rep').prefetch_related('stops__customer')
    serializer_class = RouteSerializer
    permission_map = {'list': 'routes.view', 'retrieve': 'routes.view', 'create': 'routes.manage', 'update': 'routes.manage', 'partial_update': 'routes.manage', 'destroy': 'routes.manage'}
    @action(detail=True, methods=['post'], url_path='save-plan')
    def save_plan(self, request, pk=None):
        serializer = RoutePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        route = self.get_object()
        route.route_plan = serializer.validated_data
        route.save(update_fields=['route_plan'])
        return Response(self.get_serializer(route).data)

class RouteStopViewSet(DeliveryPermissionViewSet):
    queryset = RouteStop.objects.select_related('route', 'customer')
    serializer_class = RouteStopSerializer
    permission_map = {'list': 'routes.view', 'retrieve': 'routes.view', 'create': 'routes.manage', 'update': 'routes.manage', 'partial_update': 'routes.manage', 'destroy': 'routes.manage'}

class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.select_related('route_stop__customer', 'user')
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    permission_map = {'list': 'visits.view', 'retrieve': 'visits.view', 'create': 'visits.create', 'update': 'visits.create', 'partial_update': 'visits.create', 'destroy': 'visits.create', 'check_in': 'visits.create', 'check_out': 'visits.create'}
    def get_permissions(self):
        self.required_permission = self.permission_map.get(self.action, 'visits.view')
        return super().get_permissions()
    def perform_create(self, serializer): serializer.save(user=self.request.user)
    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        try: visit = start_visit(self.get_object(), latitude=request.data.get('latitude'), longitude=request.data.get('longitude'))
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(visit).data)
    @action(detail=True, methods=['post'], url_path='check-out')
    def check_out(self, request, pk=None):
        try: visit = finish_visit(self.get_object(), latitude=request.data.get('latitude'), longitude=request.data.get('longitude'), note=request.data.get('note', ''))
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(visit).data)

class GPSTrackViewSet(viewsets.ModelViewSet):
    queryset = GPSTrack.objects.select_related('user', 'route')
    serializer_class = GPSTrackSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'visits.create'
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class VehicleViewSet(DeliveryPermissionViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

class DeliveryTripViewSet(DeliveryPermissionViewSet):
    queryset = DeliveryTrip.objects.select_related('route', 'vehicle', 'driver').prefetch_related('stops__invoice')
    serializer_class = DeliveryTripSerializer
    permission_map = {'list': 'delivery.view', 'retrieve': 'delivery.view', 'create': 'delivery.manage', 'update': 'delivery.manage', 'partial_update': 'delivery.manage', 'destroy': 'delivery.manage', 'start': 'delivery.manage'}
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        try: trip = start_trip(self.get_object())
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(self.get_serializer(trip).data)

class DeliveryStopViewSet(DeliveryPermissionViewSet):
    queryset = DeliveryStop.objects.select_related('trip', 'invoice__customer')
    serializer_class = DeliveryStopSerializer
    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        s = DeliveryActionSerializer(data=request.data); s.is_valid(raise_exception=True)
        try: attempt = record_delivery(self.get_object(), user=request.user, **s.validated_data)
        except ValidationError as exc: return Response({'detail': str(exc)}, status=400)
        return Response(DeliveryAttemptSerializer(attempt).data, status=201)

class DeliveryAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryAttempt.objects.select_related('stop__invoice', 'recorded_by')
    serializer_class = DeliveryAttemptSerializer
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = 'delivery.view'
