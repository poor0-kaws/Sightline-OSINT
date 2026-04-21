"""CSV connector shell."""

# `Path` makes file path handling explicit and easy to read.
from pathlib import Path

# `BaseConnector` gives this connector a shared shape.
from backend.connectors.base import BaseConnector
from backend.schemas.ingestion import SourceKind


class CSVConnector(BaseConnector):
    """Connector for CSV file uploads."""

    source_kind = SourceKind.CSV
    label = "CSV Upload"
    description = "Reads rows from a user-provided CSV file."
    example_location = "/tmp/people.csv"
    raw_shape_summary = "Flat rows with column names and values"

    def get_preview_raw_records(self) -> list[dict]:
        """Return a simple example of raw CSV rows."""
        file_name = Path(self.source_config.location).name
        return [
            {
                "record_id": f"{self.source_config.source_id}-row-1",
                "file_name": file_name,
                "row_number": 1,
                "columns": {
                    "name": "Maya Patel",
                    "email": "maya@example.com",
                    "company": "Northwind Labs",
                },
            }
        ]
