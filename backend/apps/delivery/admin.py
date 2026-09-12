from django.contrib import admin
from .models import Route, RouteStop, Visit, GPSTrack, Vehicle, DeliveryTrip, DeliveryStop, DeliveryAttempt
for model in (Route, RouteStop, Visit, GPSTrack, Vehicle, DeliveryTrip, DeliveryStop, DeliveryAttempt):
    admin.site.register(model)
