"""Service layer for the data source architecture section."""

from backend.connectors import build_preview_response
from backend.connectors import list_provider_definitions
from backend.connectors import run_source_request
from backend.schemas.ingestion import ProviderDefinition
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceRequest
from backend.storage import save_raw_response_safely


class IngestionService:
    """Owns the source-adapter layer."""

    def list_supported_providers(self) -> list[ProviderDefinition]:
        """Return the providers from the architecture note."""
        return list_provider_definitions()

    def preview_provider_response(self, provider: ProviderKind | str) -> RawProviderResponse:
        """Return a sample raw wrapper for one provider."""
        return build_preview_response(provider)

    def run_source_request(self, source_request: SourceRequest) -> RawProviderResponse:
        """Run one source request, then try to save the raw response."""
        response = run_source_request(source_request)
        save_raw_response_safely(
            source_config=source_request.source,
            raw_response=response,
        )
        return response
