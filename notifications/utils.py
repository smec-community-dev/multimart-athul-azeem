from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from .models import Notification
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


def _store_and_send(user_id: int, title: str, body: str, extra=None, group_name: str = ""):
    extra = extra or {}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning(f"❌ User not found: {user_id}")
        return

    # ✅ SAVE TO DATABASE
    try:
        notification = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            extra=extra,
        )
        logger.info(f"✅ Notification saved → ID: {notification.id}")
    except Exception as e:
        logger.error(f"❌ DB save failed: {e}")
        return

    # ✅ SEND VIA WEBSOCKET
    try:
        channel_layer = get_channel_layer()

        if not channel_layer:
            logger.error("❌ Channel layer not configured")
            return

        logger.info(f"📡 Sending to group → {group_name}")

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
                },
            },
        )

        logger.info(f"🚀 Notification sent → {group_name}")

    except Exception as e:
        logger.error(f"❌ WebSocket send failed: {e}")


def notify_seller(seller_user_id: int, title: str, body: str, extra=None):
    logger.info(f"🔔 notify_seller called → {seller_user_id}")

    _store_and_send(
        user_id=seller_user_id,
        title=title,
        body=body,
        extra=extra,
        group_name=f"seller_{seller_user_id}",
    )


def notify_user(user_id: int, title: str, body: str, extra=None):
    logger.info(f"🔔 notify_user called → {user_id}")

    _store_and_send(
        user_id=user_id,
        title=title,
        body=body,
        extra=extra,
        group_name=f"user_{user_id}",
    )
