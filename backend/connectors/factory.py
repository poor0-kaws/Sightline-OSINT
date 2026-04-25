"""Factory for source adapters."""

from __future__ import annotations

from typing import Any

from backend.connectors.api_connector import CrtShAdapter
from backend.connectors.api_connector import IPinfoAdapter
from backend.connectors.api_connector import NominatimAdapter
from backend.connectors.api_connector import OpenSkyAdapter
from backend.connectors.base import BaseSourceAdapter
from backend.connectors.upload_connector import CSVUploadAdapter
from backend.connectors.upload_connector import ManualInputAdapter
from backend.connectors.webhook_connector import WebhookAdapter
from backend.schemas.ingestion import ProviderDefinition
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceRequest
from backend.settings import get_settings
from backend.utils.values import clean_int
from backend.utils.values import clean_text


ADAPTER_BY_PROVIDER: dict[ProviderKind, type[BaseSourceAdapter]] = {
    ProviderKind.IPINFO: IPinfoAdapter,
    ProviderKind.CRT_SH: CrtShAdapter,
    ProviderKind.OPENSKY: OpenSkyAdapter,
    ProviderKind.NOMINATIM: NominatimAdapter,
    ProviderKind.WEBHOOK: WebhookAdapter,
    ProviderKind.CSV_UPLOAD: CSVUploadAdapter,
    ProviderKind.MANUAL_INPUT: ManualInputAdapter,
}


def _coerce_provider(provider: ProviderKind | str) -> ProviderKind:
    """Turn maybe-string provider values into the enum."""
    if isinstance(provider, ProviderKind):
        return provider

    try:
        return ProviderKind(str(provider).strip().lower())
    except ValueError as error:
        raise ValueError(f"Unsupported provider: {provider}") from error


def build_default_source_config(provider: ProviderKind | str) -> SourceConfig:
    """Build a readable demo config for one provider."""
    settings = get_settings()
    provider = _coerce_provider(provider)
    adapter_class = ADAPTER_BY_PROVIDER[provider]
    return SourceConfig(
        source_id=f"{provider.value}-demo",
        source_kind=adapter_class.source_kind,
        provider=provider,
        location=adapter_class.example_location,
        display_name=adapter_class.label,
        timeout_seconds=settings.request_timeout_seconds,
    )


def create_adapter(source_config: SourceConfig | object) -> BaseSourceAdapter:
    """Create the right adapter for one config-like object."""
    settings = get_settings()
    provider = _coerce_provider(getattr(source_config, "provider", ""))
    adapter_class = ADAPTER_BY_PROVIDER[provider]

    safe_config = SourceConfig(
        source_id=clean_text(getattr(source_config, "source_id", "")),
        source_kind=adapter_class.source_kind,
        provider=provider,
        location=clean_text(getattr(source_config, "location", "")),
        display_name=clean_text(getattr(source_config, "display_name", "")),
        timeout_seconds=clean_int(
            getattr(source_config, "timeout_seconds", settings.request_timeout_seconds),
            default=settings.request_timeout_seconds,
        ),
    )
    return adapter_class(safe_config)


def list_provider_definitions() -> list[ProviderDefinition]:
    """Return human-friendly definitions for all supported providers."""
    definitions: list[ProviderDefinition] = []

    for provider in ProviderKind:
        adapter = create_adapter(build_default_source_config(provider))
        definitions.append(adapter.describe_provider())

    return definitions


def build_preview_response(provider: ProviderKind | str) -> RawProviderResponse:
    """Return a sample raw response for one provider."""
    adapter = create_adapter(build_default_source_config(provider))
    return adapter.preview_response()


def run_source_request(source_request: SourceRequest) -> RawProviderResponse:
    """Run one source request through the correct adapter."""
    adapter = create_adapter(source_request.source)
    return adapter.fetch(source_request.query)
