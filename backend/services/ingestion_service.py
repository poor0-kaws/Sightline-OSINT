"""Service layer for the data source architecture section."""

from __future__ import annotations

from typing import Any

from backend.connectors import build_preview_response
from backend.connectors import list_provider_definitions
from backend.connectors import run_source_request
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderDefinition
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceKind
from backend.schemas.ingestion import SourceRequest
from backend.schemas.storage import SavedRawRecord
from backend.storage import save_raw_response_safely
from backend.utils.time import utc_now_iso
from backend.utils.values import clean_text


class IngestionService:
    """Owns the source-adapter layer."""

    def list_supported_providers(self) -> list[ProviderDefinition]:
        """Return the providers from the architecture note."""
        return list_provider_definitions()

    def preview_provider_response(self, provider: ProviderKind | str) -> RawProviderResponse:
        """Return a sample raw wrapper for one provider."""
        return build_preview_response(provider)

    def run_source_request(self, source_request: object) -> RawProviderResponse:
        """Run one source request and turn hard crashes into error wrappers."""
        response, _saved_raw_record = self.run_source_request_with_record(source_request)
        return response

    def run_source_request_with_record(
        self,
        source_request: object,
    ) -> tuple[RawProviderResponse, SavedRawRecord | None]:
        """Run one source request, save the raw response, and return both results."""
        response = self._build_source_response(source_request)
        saved_raw_record = self._try_save_response(source_request=source_request, raw_response=response)
        return response, saved_raw_record

    def _build_source_response(self, source_request: object) -> RawProviderResponse:
        """Build one raw provider response with service-level crash protection."""
        if not self._looks_like_source_request(source_request):
            return self._build_service_error_response(
                source_request=source_request,
                error_code=ErrorCode.INVALID_SOURCE_REQUEST,
                message="Source request must include a source config and a query.",
            )

        try:
            response = run_source_request(source_request)
        except ValueError as error:
            error_message = clean_text(str(error)) or "Unexpected source-layer error."
            error_code = ErrorCode.UNEXPECTED_SOURCE_ERROR

            if error_message.startswith("Unsupported provider:"):
                error_code = ErrorCode.UNSUPPORTED_PROVIDER

            return self._build_service_error_response(
                source_request=source_request,
                error_code=error_code,
                message=error_message,
                metadata={"exception_type": type(error).__name__},
            )
        except Exception as error:
            return self._build_service_error_response(
                source_request=source_request,
                error_code=ErrorCode.UNEXPECTED_SOURCE_ERROR,
                message=clean_text(str(error)) or "Unexpected source-layer error.",
                metadata={"exception_type": type(error).__name__},
            )

        if not isinstance(response, RawProviderResponse):
            return self._build_service_error_response(
                source_request=source_request,
                error_code=ErrorCode.INVALID_PROVIDER_RESPONSE,
                message="Source adapter returned an invalid response shape.",
                metadata={"returned_type": type(response).__name__},
            )

        return response

    def _try_save_response(
        self,
        source_request: object,
        raw_response: RawProviderResponse,
    ) -> SavedRawRecord | None:
        """Try to save a raw response when a source config is available."""
        source_config = getattr(source_request, "source", None)
        if source_config is None:
            return None

        return save_raw_response_safely(source_config=source_config, raw_response=raw_response)

    def _looks_like_source_request(self, source_request: object) -> bool:
        """Check for the minimum shape needed to route one request."""
        if source_request is None:
            return False

        if not hasattr(source_request, "source"):
            return False

        if not hasattr(source_request, "query"):
            return False

        source_config = getattr(source_request, "source", None)
        if source_config is None:
            return False

        if not hasattr(source_config, "provider"):
            return False

        return True

    def _build_service_error_response(
        self,
        source_request: object,
        error_code: ErrorCode,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> RawProviderResponse:
        """Build a shared error wrapper for service-level failures."""
        error_metadata = dict(metadata or {})

        requested_provider = clean_text(self._extract_provider_text(source_request))
        if requested_provider:
            error_metadata["requested_provider"] = requested_provider

        return RawProviderResponse(
            provider=self._extract_provider(source_request),
            source_type=self._extract_source_type(source_request),
            query=self._extract_query(source_request),
            fetched_at=utc_now_iso(),
            status=FetchStatus.ERROR,
            raw_data=None,
            error=ProviderError(code=error_code.value, message=message),
            metadata=error_metadata,
        )

    def _extract_provider(self, source_request: object) -> ProviderKind:
        """Read a provider from the request, or fall back safely."""
        provider_text = self._extract_provider_text(source_request)
        if isinstance(provider_text, ProviderKind):
            return provider_text

        try:
            return ProviderKind(clean_text(provider_text).lower())
        except ValueError:
            return ProviderKind.IPINFO

    def _extract_provider_text(self, source_request: object) -> object:
        """Read the raw provider value from the request."""
        source_config = getattr(source_request, "source", None)
        return getattr(source_config, "provider", None)

    def _extract_source_type(self, source_request: object) -> SourceKind:
        """Read a source type from the request, or fall back safely."""
        source_config = getattr(source_request, "source", None)
        source_type = getattr(source_config, "source_kind", None)
        if isinstance(source_type, SourceKind):
            return source_type

        try:
            return SourceKind(clean_text(source_type).lower())
        except ValueError:
            return SourceKind.API

    def _extract_query(self, source_request: object) -> Any:
        """Read the original query if it exists."""
        if hasattr(source_request, "query"):
            return getattr(source_request, "query")

        return None
