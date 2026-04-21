"""Manual connector shell."""

# `BaseConnector` gives this connector a shared interface.
from backend.connectors.base import BaseConnector
from backend.schemas.ingestion import SourceKind


class ManualConnector(BaseConnector):
    """Connector for analyst-entered records."""

    source_kind = SourceKind.MANUAL
    label = "Manual Input"
    description = "Lets an analyst type in a fact, note, or lead by hand."
    example_location = "manual://analyst-note"
    raw_shape_summary = "Small hand-entered records with free-text fields"

    def get_preview_raw_records(self) -> list[dict]:
        """Return a simple example of manual input data."""
        return [
            {
                "record_id": f"{self.source_config.source_id}-note-1",
                "entered_by": "analyst",
                "note": "Possible link between Maya Patel and portal.example.com",
                "fields": {
                    "person_name": "Maya Patel",
                    "domain": "portal.example.com",
                },
            }
        ]
