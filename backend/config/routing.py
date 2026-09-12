from django.urls import path
from .consumers import LiveDashboardConsumer

websocket_urlpatterns = [path('ws/live/', LiveDashboardConsumer.as_asgi())]
