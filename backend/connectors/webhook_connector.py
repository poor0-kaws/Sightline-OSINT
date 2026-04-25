"""Webhook source adapter."""

from __future__ import annotations

from typing import Any

from backend.connectors.base import BaseSourceAdapter
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import QueryType
from backend.schemas.ingestion import SourceKind


class WebhookAdapter(BaseSourceAdapter):
    """Adapter for inbound webhook payloads."""

    provider = ProviderKind.WEBHOOK
    source_kind = SourceKind.WEBHOOK
    label = "Webhook"
    description = "Accepts raw webhook payloads exactly as they are received."
    accepted_query_types = [QueryType.PAYLOAD_BODY]
    example_query = {
        "event_type": "breach.alert",
        "payload": {"email": "maya@example.com", "domain": "example.com"},
    }
    example_location = "webhook://intel-feed/high-priority"

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        if not isinstance(query, dict):
            return ProviderError(
                code=ErrorCode.BAD_QUERY_TYPE.value,
                message="Webhook input must be a dictionary payload.",
            )

        if "event_type" not in query:
            return ProviderError(
                code=ErrorCode.MISSING_REQUIRED_FIELD.value,
                message="Webhook payload needs an event_type field.",
            )

        if "payload" not in query:
            return ProviderError(
                code=ErrorCode.MISSING_REQUIRED_FIELD.value,
                message="Webhook payload needs a payload field.",
            )

        return None

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": query,
            "metadata": {"delivery_mode": "push", "location": self.source_config.location},
        }
