import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging  # ← NEW: For optional logging (optional, but good for debugging)

logger = logging.getLogger(__name__)  # ← NEW: Logger instance

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning(f"Unauthorized WebSocket connect attempt from {self.channel_name}")
            await self.close()  # ← IMPROVED: Close without accepting
            return

        # ← NEW: Dynamic group based on user type
        if hasattr(user, 'seller_details'):
            self.group_name = f"seller_{user.id}"
        else:
            self.group_name = f"user_{user.id}"

        # Add to group and accept
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connected for user {user.id} in group {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):  # ← IMPROVED: Guard against unset group_name
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"WebSocket disconnected for group {self.group_name}, code: {close_code}")
        else:
            logger.warning(f"Disconnect without group: {self.channel_name}, code: {close_code}")

    async def send_notification(self, event):
        payload = event.get("payload", {})
        # ← OPTIONAL: Add sender/user context if needed for frontend
        payload['group_type'] = self.group_name.split('_')[0]  # e.g., 'seller' or 'user'
        await self.send(text_data=json.dumps(payload))
        logger.debug(f"Notification sent to {self.group_name}: {payload.get('title', 'No title')}")