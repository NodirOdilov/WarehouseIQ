"""WebSocket consumers for real-time stock alerts."""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class StockAlertConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that broadcasts stock alerts to connected clients.
    Clients connect to ws/stock-alerts/ to receive real-time notifications.
    """

    async def connect(self):
        self.group_name = "stock_alerts"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()

        logger.info(
            "WebSocket client connected to stock_alerts: %s",
            self.channel_name,
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )
        logger.info(
            "WebSocket client disconnected from stock_alerts: %s (code=%s)",
            self.channel_name,
            close_code,
        )

    async def receive(self, text_data):
        """Handle incoming messages from clients (e.g., acknowledgments)."""
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "acknowledge":
                alert_id = data.get("alert_id")
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "alert.acknowledged",
                        "data": {
                            "alert_id": alert_id,
                            "acknowledged_by": self.channel_name,
                        },
                    },
                )
            elif action == "subscribe_warehouse":
                warehouse_id = data.get("warehouse_id")
                if warehouse_id:
                    wh_group = f"stock_alerts_{warehouse_id}"
                    await self.channel_layer.group_add(
                        wh_group,
                        self.channel_name,
                    )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "error": "Invalid JSON message.",
            }))

    async def stock_alert(self, event):
        """Send a stock alert to the WebSocket client."""
        await self.send(text_data=json.dumps({
            "type": "stock_alert",
            "data": event["data"],
        }))

    async def alert_acknowledged(self, event):
        """Notify clients that an alert has been acknowledged."""
        await self.send(text_data=json.dumps({
            "type": "alert_acknowledged",
            "data": event["data"],
        }))
