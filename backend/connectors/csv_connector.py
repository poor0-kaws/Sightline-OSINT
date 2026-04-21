"""CSV connector shell."""

# `Path` makes file path handling explicit and easy to read.
from pathlib import Path

# `BaseConnector` gives this connector a shared shape.
from backend.connectors.base import BaseConnector


# We still use the same connector class shape so every source plugs into one pipeline.
class CSVConnector(BaseConnector):
    """Connector shell for CSV files."""

    async def fetch_raw_records(self) -> list[dict]:
        """Read rows from a CSV file."""
        # TODO [CORE]: open the CSV file, validate headers, and read rows safely.
        _ = Path(self.source_config.location)
        return []

    async def normalize_records(self) -> list[dict]:
        """Normalize CSV rows into the shared record shape."""
        # TODO [CORE]: decide which CSV columns map to which normalized fields.
        return []

