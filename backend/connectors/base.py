"""Base adapter for raw data source providers."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from backend.schemas.ingestion import FetchStatus
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import ProviderDefinition
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import QueryType
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceKind
from backend.settings import get_settings
from backend.utils.http_client import HTTPClientError
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
        settings = get_settings()
        source_id = clean_text(getattr(source_config, "source_id", ""))
        location = clean_text(getattr(source_config, "location", ""))
        display_name = clean_text(getattr(source_config, "display_name", ""))

        if not source_id:
            source_id = f"{self.provider.value}-source"

        if not location:
            location = self.example_location

        if not display_name:
            display_name = self.label

        timeout_seconds = clean_int(
            getattr(source_config, "timeout_seconds", settings.request_timeout_seconds),
            default=settings.request_timeout_seconds,
        )

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
            return ProviderError(
                code=ErrorCode.EMPTY_QUERY.value,
                message="This provider needs a query or input payload.",
            )

        if isinstance(query, str) and not query.strip():
            return ProviderError(
                code=ErrorCode.EMPTY_QUERY.value,
                message="This provider needs a query or input payload.",
            )

        if isinstance(query, dict) and not query:
            return ProviderError(
                code=ErrorCode.EMPTY_QUERY.value,
                message="This provider needs a query or input payload.",
            )

        if isinstance(query, list) and not query:
            return ProviderError(
                code=ErrorCode.EMPTY_QUERY.value,
                message="This provider needs a query or input payload.",
            )

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

    def _build_live_error_result(self, error: HTTPClientError, *, mode: str) -> dict[str, Any]:
        """Turn a live provider failure into the shared outer wrapper payload."""
        error_code = ErrorCode.PROVIDER_HTTP_ERROR
        if error.failure_kind == "timeout":
            error_code = ErrorCode.PROVIDER_TIMEOUT
        elif error.failure_kind == "network_error":
            error_code = ErrorCode.PROVIDER_NETWORK_ERROR
        elif error.failure_kind == "invalid_json":
            error_code = ErrorCode.PROVIDER_BAD_RESPONSE
        elif error.status_code == 429:
            error_code = ErrorCode.PROVIDER_RATE_LIMITED

        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=error_code.value,
                message=str(error),
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": error.status_code or 0,
            },
        }

    def _build_bad_response_result(
        self,
        *,
        message: str,
        mode: str,
        response_code: int,
    ) -> dict[str, Any]:
        """Return a shared payload for malformed provider data."""
        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=ErrorCode.PROVIDER_BAD_RESPONSE.value,
                message=message,
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": response_code,
            },
        }

    def _build_no_results_result(
        self,
        *,
        raw_data: Any,
        mode: str,
        response_code: int,
        request_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a shared payload for a clean empty provider result."""
        result_metadata: dict[str, Any] = {
            "provider": self.provider.value,
            "mode": mode,
            "response_code": response_code,
            "request_url": request_url,
        }
        result_metadata.update(metadata or {})

        return {
            "status": FetchStatus.NO_RESULTS,
            "raw_data": raw_data,
            "metadata": result_metadata,
        }
