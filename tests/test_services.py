"""Tests for the source-layer service."""

import pytest

import backend.services.ingestion_service as ingestion_service_module
import backend.storage.raw_storage_repository as raw_storage_repository_module
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceRequest
from backend.schemas.ingestion import SourceKind
from backend.services.ingestion_service import IngestionService
from backend.storage.raw_storage_repository import FileRawStorageRepository


def test_service_lists_supported_providers() -> None:
    """The ingestion service should expose all provider definitions."""
    service = IngestionService()
    definitions = service.list_supported_providers()

    assert len(definitions) == 7
    assert definitions[0].provider == ProviderKind.IPINFO


def test_service_accepts_string_provider_for_preview() -> None:
    """The preview method should accept a plain provider string."""
    service = IngestionService()
    response = service.preview_provider_response("webhook")

    assert response.provider == ProviderKind.WEBHOOK
    assert response.raw_data["event_type"] == "breach.alert"


def test_service_run_source_request_saves_raw_response(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running a source request should save the raw wrapper to storage."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    service = IngestionService()
    source_request = SourceRequest(
        source=SourceConfig(
            source_id="case-source-1",
            provider=ProviderKind.IPINFO,
        ),
        query="8.8.8.8",
    )

    response = service.run_source_request(source_request)
    repository = FileRawStorageRepository(tmp_path)
    saved_records = repository.list_raw_responses()

    assert response.provider == ProviderKind.IPINFO
    assert len(saved_records) == 1
    assert saved_records[0].source_id == "case-source-1"
    assert saved_records[0].raw_data["ip"] == "8.8.8.8"


def test_service_run_source_request_does_not_crash_if_storage_save_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Storage errors should not break the source request path."""

    def explode(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(raw_storage_repository_module, "save_raw_response", explode)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO),
            query="8.8.8.8",
        )
    )

    assert response.provider == ProviderKind.IPINFO
    assert response.raw_data["ip"] == "8.8.8.8"


def test_service_run_source_request_saves_error_responses_too(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even invalid provider requests should leave behind saved raw wrappers."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    service = IngestionService()

    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-2",
                provider=ProviderKind.CRT_SH,
            ),
            query="bad domain",
        )
    )

    repository = FileRawStorageRepository(tmp_path)
    saved_records = repository.list_raw_responses()

    assert response.status == FetchStatus.ERROR
    assert len(saved_records) == 1
    assert saved_records[0].status == FetchStatus.ERROR
    assert saved_records[0].error is not None


def test_service_run_source_request_returns_clean_error_for_invalid_request_shape() -> None:
    """Malformed request objects should become error wrappers, not crashes."""
    service = IngestionService()
    response = service.run_source_request(object())

    assert response.status == FetchStatus.ERROR
    assert response.error.code == ErrorCode.INVALID_SOURCE_REQUEST.value


def test_service_run_source_request_returns_clean_error_for_unsupported_provider() -> None:
    """Unsupported providers should become service-level error wrappers."""

    class BadSourceConfig:
        provider = "not-a-real-provider"
        source_id = "broken-source"
        source_kind = "api"

    class BadSourceRequest:
        source = BadSourceConfig()
        query = "8.8.8.8"

    service = IngestionService()
    response = service.run_source_request(BadSourceRequest())

    assert response.status == FetchStatus.ERROR
    assert response.error.code == ErrorCode.UNSUPPORTED_PROVIDER.value
    assert response.metadata["requested_provider"] == "not-a-real-provider"


def test_service_run_source_request_returns_clean_error_if_dispatch_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected source-layer crashes should become error wrappers."""

    def explode(_source_request: object) -> RawProviderResponse:
        raise RuntimeError("adapter boom")

    monkeypatch.setattr(ingestion_service_module, "run_source_request", explode)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO),
            query="8.8.8.8",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == ErrorCode.UNEXPECTED_SOURCE_ERROR.value
    assert response.metadata["exception_type"] == "RuntimeError"


def test_service_run_source_request_returns_clean_error_for_invalid_adapter_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrong response shapes from the source layer should be wrapped safely."""

    def bad_return(_source_request: object) -> dict[str, str]:
        return {"not": "a raw provider response"}

    monkeypatch.setattr(ingestion_service_module, "run_source_request", bad_return)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO),
            query="8.8.8.8",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == ErrorCode.INVALID_PROVIDER_RESPONSE.value
    assert response.metadata["returned_type"] == "dict"
