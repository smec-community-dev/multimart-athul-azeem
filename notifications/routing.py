from django.urls import re_path
from . import consumers  # Assuming consumers.py is in the same app

websocket_urlpatterns = [
    # ← UPDATED: Both paths point to the same generic consumer
    re_path(r'ws/seller/not/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/user/not/$', consumers.NotificationConsumer.as_asgi()),
    # ← NEW: Optional unified path for future JS updates
    re_path(r'ws/not/$', consumers.NotificationConsumer.as_asgi()),
]