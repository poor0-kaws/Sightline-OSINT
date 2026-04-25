"""Upload and manual-entry source adapters."""

from __future__ import annotations

from typing import Any

from backend.connectors.base import BaseSourceAdapter
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import QueryType
from backend.schemas.ingestion import SourceKind


class CSVUploadAdapter(BaseSourceAdapter):
    """Adapter for uploaded CSV rows."""

    provider = ProviderKind.CSV_UPLOAD
    source_kind = SourceKind.CSV
    label = "CSV Upload"
    description = "Accepts original rows from an uploaded CSV file."
    accepted_query_types = [QueryType.FILE_ROWS]
    example_query = [
        {"name": "Maya Patel", "email": "maya@example.com"},
        {"name": "Omar Ruiz", "email": "omar@example.com"},
    ]
    example_location = "upload://case-import.csv"

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        if not isinstance(query, list):
            return ProviderError(
                code=ErrorCode.BAD_QUERY_TYPE.value,
                message="CSV upload expects a list of row dictionaries.",
            )

        if not all(isinstance(row, dict) for row in query):
            return ProviderError(
                code=ErrorCode.BAD_QUERY_TYPE.value,
                message="CSV upload rows must each be a dictionary.",
            )

        return None

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": query,
            "metadata": {"row_count": len(query), "location": self.source_config.location},
        }


class ManualInputAdapter(BaseSourceAdapter):
    """Adapter for analyst-entered records."""

    provider = ProviderKind.MANUAL_INPUT
    source_kind = SourceKind.MANUAL
    label = "Manual Input"
    description = "Accepts hand-entered fields from an analyst."
    accepted_query_types = [QueryType.MANUAL_FIELDS]
    example_query = {
        "note": "Possible link between Maya Patel and portal.example.com",
        "person_name": "Maya Patel",
        "domain": "portal.example.com",
    }
    example_location = "manual://analyst-note"

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        if not isinstance(query, dict):
            return ProviderError(
                code=ErrorCode.BAD_QUERY_TYPE.value,
                message="Manual input expects a dictionary of fields.",
            )

        if "note" not in query:
            return ProviderError(
                code=ErrorCode.MISSING_REQUIRED_FIELD.value,
                message="Manual input requires a note field.",
            )

        return None

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": query,
            "metadata": {"entered_by": "analyst", "location": self.source_config.location},
        }
