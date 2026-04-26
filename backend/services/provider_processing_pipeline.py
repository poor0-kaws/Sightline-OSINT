"""Reusable processing pipeline for all data providers."""

from __future__ import annotations

from backend.normalization import NormalizedRecord
from backend.normalization import normalize_saved_raw_record
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind
from backend.schemas.ingestion import SourceRequest
from backend.services.ingestion_service import IngestionService


class ProviderProcessingPipeline:
    """Run the shared fetch -> save -> normalize flow for one source request."""

    def __init__(self, ingestion_service: IngestionService | None = None) -> None:
        self.ingestion_service = ingestion_service or IngestionService()

    def run(self, source_request: SourceRequest | object) -> NormalizedRecord:
        """Fetch raw data, save it, then normalize the saved raw record."""
        raw_response, saved_raw_record = self.ingestion_service.run_source_request_with_record(source_request)
        if saved_raw_record is None:
            return NormalizedRecord(
                provider=self._extract_provider(source_request),
                source_type=self._extract_source_type(source_request),
                raw_record_id="",
                query=self._extract_query(source_request),
                status=FetchStatus.ERROR,
                error=ProviderError(
                    code=ErrorCode.STORAGE_SAVE_FAILED.value,
                    message="Raw response could not be saved, so normalization did not run.",
                ),
                normalized_data=None,
                metadata={
                    "raw_response_status": raw_response.status.value,
                },
            )

        return normalize_saved_raw_record(saved_raw_record)

    def _extract_provider(self, source_request: object) -> ProviderKind:
        """Read a provider from the request, or fall back safely."""
        source_config = getattr(source_request, "source", None)
        provider = getattr(source_config, "provider", None)
        if isinstance(provider, ProviderKind):
            return provider

        return ProviderKind.IPINFO

    def _extract_source_type(self, source_request: object) -> SourceKind:
        """Read a source type from the request, or fall back safely."""
        source_config = getattr(source_request, "source", None)
        source_type = getattr(source_config, "source_kind", None)
        if isinstance(source_type, SourceKind):
            return source_type

        return SourceKind.API

    def _extract_query(self, source_request: object) -> object:
        """Read the original query if it exists."""
        return getattr(source_request, "query", None)
