"""Base adapter for raw data source providers."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderDefinition
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import QueryType
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceKind
from backend.utils.time import utc_now_iso
from backend.utils.values import clean_int
from backend.utils.values import clean_text


class BaseSourceAdapter(ABC):
    """Shared behavior for every source adapter."""

    provider: ProviderKind = ProviderKind.IPINFO
    source_kind: SourceKind = SourceKind.API
    label: str = "Provider"
    description: str = "Generic data source provider"
    accepted_query_types: list[QueryType] = []
    example_query: Any = ""
    example_location: str = ""

    def __init__(self, source_config: SourceConfig) -> None:
        self.source_config = self._build_safe_source_config(source_config)

    def _build_safe_source_config(self, source_config: SourceConfig) -> SourceConfig:
        """Fill in missing config values with readable defaults."""
        source_id = clean_text(getattr(source_config, "source_id", ""))
        location = clean_text(getattr(source_config, "location", ""))
        display_name = clean_text(getattr(source_config, "display_name", ""))

        if not source_id:
            source_id = f"{self.provider.value}-source"

        if not location:
            location = self.example_location

        if not display_name:
            display_name = self.label

        timeout_seconds = clean_int(getattr(source_config, "timeout_seconds", 30), default=30)

        return SourceConfig(
            source_id=source_id,
            source_kind=self.source_kind,
            provider=self.provider,
            location=location,
            display_name=display_name,
            timeout_seconds=timeout_seconds,
        )

    def describe_provider(self) -> ProviderDefinition:
        """Return a plain-English provider definition."""
        return ProviderDefinition(
            provider=self.provider,
            source_kind=self.source_kind,
            label=self.label,
            description=self.description,
            accepted_query_types=self.accepted_query_types,
            example_query=self.example_query,
            example_location=self.example_location,
        )

    def preview_response(self) -> RawProviderResponse:
        """Return a sample raw provider wrapper."""
        return self.fetch(self.example_query)

    def fetch(self, query: Any) -> RawProviderResponse:
        """Validate the input, then wrap the provider's raw response."""
        validation_error = self.validate_query(query)
        if validation_error is not None:
            return self._build_error_response(query=query, error=validation_error)

        provider_result = self.fetch_raw_data(query)
        return self._build_success_response(query=query, provider_result=provider_result)

    def validate_query(self, query: Any) -> ProviderError | None:
        """Reject obviously unusable input before calling the provider."""
        if query is None:
            return ProviderError(code="empty_query", message="This provider needs a query or input payload.")

        if isinstance(query, str) and not query.strip():
            return ProviderError(code="empty_query", message="This provider needs a query or input payload.")

        if isinstance(query, dict) and not query:
            return ProviderError(code="empty_query", message="This provider needs a query or input payload.")

        if isinstance(query, list) and not query:
            return ProviderError(code="empty_query", message="This provider needs a query or input payload.")

        return self.validate_provider_query(query)

    @abstractmethod
    def validate_provider_query(self, query: Any) -> ProviderError | None:
        """Reject input that does not fit this provider."""

    @abstractmethod
    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        """Return the provider's raw payload and metadata."""

    def _build_success_response(self, query: Any, provider_result: dict[str, Any]) -> RawProviderResponse:
        """Wrap a provider result in the shared outer shape."""
        return RawProviderResponse(
            provider=self.provider,
            source_type=self.source_kind,
            query=query,
            fetched_at=self._timestamp(),
            status=provider_result.get("status", FetchStatus.SUCCESS),
            raw_data=provider_result.get("raw_data"),
            error=provider_result.get("error"),
            metadata=provider_result.get("metadata", {}),
        )

    def _build_error_response(self, query: Any, error: ProviderError) -> RawProviderResponse:
        """Wrap a provider-level failure in the shared outer shape."""
        return RawProviderResponse(
            provider=self.provider,
            source_type=self.source_kind,
            query=query,
            fetched_at=self._timestamp(),
            status=FetchStatus.ERROR,
            raw_data=None,
            error=error,
            metadata={"location": self.source_config.location},
        )

    def _timestamp(self) -> str:
        """Return a UTC timestamp string."""
        return utc_now_iso()
