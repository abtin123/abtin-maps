from rest_framework.routers import DefaultRouter
from django.urls import include, path
from .views import RouteViewSet, RouteStopViewSet, VisitViewSet, GPSTrackViewSet, VehicleViewSet, DeliveryTripViewSet, DeliveryStopViewSet, DeliveryAttemptViewSet
router = DefaultRouter()
router.register('routes', RouteViewSet)
router.register('route-stops', RouteStopViewSet)
router.register('visits', VisitViewSet)
router.register('gps-tracks', GPSTrackViewSet)
router.register('vehicles', VehicleViewSet)
router.register('trips', DeliveryTripViewSet)
router.register('delivery-stops', DeliveryStopViewSet)
router.register('delivery-attempts', DeliveryAttemptViewSet)
urlpatterns = [path('', include(router.urls))]
