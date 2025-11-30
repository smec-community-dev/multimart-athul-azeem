from django.urls import re_path
from .consumers import SellerNotificationConsumer, UserNotificationConsumer

websocket_urlpatterns = [
    re_path(r"ws/seller/notifications/$", SellerNotificationConsumer.as_asgi()),
    re_path(r"ws/user/notifications/$", UserNotificationConsumer.as_asgi()),
]
