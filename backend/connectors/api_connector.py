"""API connector shell."""

# `BaseConnector` gives this connector a shared interface.
from backend.connectors.base import BaseConnector
from backend.schemas.ingestion import SourceKind


class APIConnector(BaseConnector):
    """Connector for third-party APIs."""

    source_kind = SourceKind.API
    label = "API"
    description = "Pulls structured records from a remote API endpoint."
    example_location = "https://api.shodan.io/shodan/host/search"
    raw_shape_summary = "JSON payloads with nested fields"

    def get_preview_raw_records(self) -> list[dict]:
        """Return a simple example of raw API output."""
        return [
            {
                "record_id": f"{self.source_config.source_id}-response-1",
                "endpoint": self.source_config.location,
                "query": "example.com",
                "response_body": {
                    "matches": [
                        {
                            "ip": "203.0.113.10",
                            "hostnames": ["portal.example.com"],
                            "org": "Example Hosting",
                        }
                    ]
                },
            }
        ]
