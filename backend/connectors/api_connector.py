"""API connector shell."""

# `AsyncClient` is the HTTP client used for remote API calls.
from backend.utils.optional_deps import AsyncClient

# `BaseConnector` gives this connector a shared interface.
from backend.connectors.base import BaseConnector


# We keep API ingestion async because network work spends most of its time waiting.
class APIConnector(BaseConnector):
    """Connector shell for third-party APIs."""

    async def fetch_raw_records(self) -> list[dict]:
        """Fetch raw records from a remote API."""
        # TODO [CORE]: handle auth, pagination, backoff, and response parsing.
        async with AsyncClient() as client:
            _ = client
            return []

    async def normalize_records(self) -> list[dict]:
        """Normalize raw API records into a shared shape."""
        # TODO [CORE]: map API-specific payloads into your canonical entity/event schema.
        return []

