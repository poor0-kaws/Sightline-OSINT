"""Webhook connector shell."""

# `BaseConnector` gives this connector a shared interface.
from backend.connectors.base import BaseConnector
from backend.schemas.ingestion import SourceKind


class WebhookConnector(BaseConnector):
    """Connector for webhook-delivered payloads."""

    source_kind = SourceKind.WEBHOOK
    label = "Webhook"
    description = "Accepts push-based payloads sent into the platform."
    example_location = "webhook://intel-feed/high-priority"
    raw_shape_summary = "Event payloads with metadata and nested bodies"

    def get_preview_raw_records(self) -> list[dict]:
        """Return a simple example of raw webhook events."""
        return [
            {
                "record_id": f"{self.source_config.source_id}-event-1",
                "event_type": "breach.alert",
                "delivered_at": "2026-04-21T12:00:00Z",
                "payload": {
                    "email": "maya@example.com",
                    "domain": "example.com",
                },
            }
        ]
