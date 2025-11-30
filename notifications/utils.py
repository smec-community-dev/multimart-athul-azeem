from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

def _store_and_send(user_id: int, title: str, body: str, extra: dict, group_name: str):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        extra=extra,
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "send_notification",
            "payload": {
                "title": title,
                "body": body,
                "notification_id": notification.id,
                "extra": extra,
                "created_at": notification.created_at.isoformat(),
            }
        }
    )

def notify_seller(seller_user_id: int, title: str, body: str, extra=None):
    _store_and_send(
        user_id=seller_user_id,
        title=title,
        body=body,
        extra=extra,
        group_name=f"seller_{seller_user_id}"
    )

def notify_user(user_id: int, title: str, body: str, extra=None):
    _store_and_send(
        user_id=user_id,
        title=title,
        body=body,
        extra=extra,
        group_name=f"user_{user_id}"
    )
