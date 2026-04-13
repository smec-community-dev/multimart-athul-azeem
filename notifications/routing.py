from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/user/not/", consumers.NotificationConsumer.as_asgi()),
    path("ws/seller/not/", consumers.NotificationConsumer.as_asgi()),
    path("ws/not/", consumers.NotificationConsumer.as_asgi()),
]
