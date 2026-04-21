"""Webhook connector shell."""

# `BaseConnector` gives this connector a shared interface.
from backend.connectors.base import BaseConnector


# We keep webhook handling in the same connector family so every source enters the same pipeline.
class WebhookConnector(BaseConnector):
    """Connector shell for webhook payloads."""

    async def fetch_raw_records(self) -> list[dict]:
        """Return raw records already delivered by a webhook."""
        # TODO [CORE]: store and replay inbound webhook payloads as normalized pipeline input.
        return []

    async def normalize_records(self) -> list[dict]:
        """Normalize webhook payloads into the shared record shape."""
        # TODO [CORE]: decide how webhook payload fields map into your canonical schema.
        return []

