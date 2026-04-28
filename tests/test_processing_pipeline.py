"""Tests for the reusable provider processing pipeline."""

from __future__ import annotations

import pytest

import backend.connectors.api_connector as api_connector_module
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceRequest
from backend.services.provider_processing_pipeline import ProviderProcessingPipeline
from backend.utils.http_client import HTTPClientError
from backend.utils.http_client import JSONResponse


def test_processing_pipeline_runs_fetch_save_and_normalize(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared pipeline should return a normalized record for a good request."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    pipeline = ProviderProcessingPipeline()

    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-1",
                provider=ProviderKind.IPINFO,
            ),
            query="8.8.8.8",
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "success"
    assert normalized_record.normalized_data["ip_address"] == "8.8.8.8"
    assert any(entity.entity_type == "ip" and entity.canonical_value == "8.8.8.8" for entity in normalized_record.entities)


def test_processing_pipeline_returns_normalized_error_for_live_provider_failure(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live provider failures should still save raw errors and normalize them cleanly."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        raise HTTPClientError("Network request timed out.", failure_kind="timeout")

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-2",
                provider=ProviderKind.NOMINATIM,
            ),
            query="Indianapolis",
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "error"
    assert normalized_record.error.code == ErrorCode.PROVIDER_TIMEOUT.value
    assert normalized_record.normalized_data is None


def test_processing_pipeline_runs_fetch_save_and_normalize_for_crt_sh(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared pipeline should save crt.sh raw data before normalizing it."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        return JSONResponse(
            status_code=200,
            data=[
                {
                    "common_name": "example.com",
                    "issuer_name": "Let's Encrypt",
                    "not_before": "2026-01-10T00:00:00Z",
                }
            ],
            url="https://crt.sh?q=example.com&output=json",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-3",
                provider=ProviderKind.CRT_SH,
            ),
            query="example.com",
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "success"
    assert normalized_record.normalized_data["certificates"][0]["common_name"] == "example.com"
    assert any(entity.entity_type == "domain" and entity.canonical_value == "example.com" for entity in normalized_record.entities)


def test_processing_pipeline_runs_fetch_save_and_normalize_for_opensky_aircraft(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared pipeline should save OpenSky raw aircraft data before normalizing it."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        return JSONResponse(
            status_code=200,
            data={
                "time": 1_777_090_400,
                "states": [
                    [
                        "abc123",
                        "AAL123",
                        "United States",
                        None,
                        None,
                        -86.1581,
                        39.7684,
                        11200.0,
                    ]
                ],
            },
            url="https://opensky-network.org/api/states/all?icao24=aal123",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-4",
                provider=ProviderKind.OPENSKY,
            ),
            query="AAL123",
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "success"
    assert normalized_record.normalized_data["aircraft"]["icao24"] == "abc123"


def test_processing_pipeline_returns_normalized_error_for_opensky_live_failure(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenSky fetch failures should still save raw errors and normalize them cleanly."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        raise HTTPClientError("Network request timed out.", failure_kind="timeout")

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-5",
                provider=ProviderKind.OPENSKY,
            ),
            query="AAL123",
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "error"
    assert normalized_record.error.code == ErrorCode.PROVIDER_TIMEOUT.value
    assert normalized_record.normalized_data is None


def test_processing_pipeline_runs_fetch_save_and_normalize_for_webhook(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared pipeline should save webhook raw data before normalizing it."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-6",
                provider=ProviderKind.WEBHOOK,
            ),
            query={
                "event_type": "breach.alert",
                "payload": {"email": "maya@example.com", "domain": "example.com"},
            },
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "success"
    assert normalized_record.normalized_data["event_type"] == "breach.alert"
    assert any(entity.entity_type == "domain" and entity.canonical_value == "example.com" for entity in normalized_record.entities)


def test_processing_pipeline_runs_fetch_save_and_normalize_for_csv_upload(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared pipeline should save CSV-upload rows before normalizing them."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-7",
                provider=ProviderKind.CSV_UPLOAD,
            ),
            query=[
                {"name": "Maya Patel", "email": "maya@example.com"},
                {"name": "Omar Ruiz", "email": "omar@example.com"},
            ],
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "success"
    assert len(normalized_record.normalized_data["rows"]) == 2


def test_processing_pipeline_runs_fetch_save_and_normalize_for_manual_input(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared pipeline should save manual-input data before normalizing it."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-8",
                provider=ProviderKind.MANUAL_INPUT,
            ),
            query={
                "note": "Possible link between Maya Patel and portal.example.com",
                "person_name": "Maya Patel",
                "domain": "portal.example.com",
            },
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "success"
    assert normalized_record.normalized_data["fields"]["domain"] == "portal.example.com"


def test_processing_pipeline_returns_normalized_error_for_webhook_validation_failure(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Webhook validation failures should still save raw errors and normalize them cleanly."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    pipeline = ProviderProcessingPipeline()
    normalized_record = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="case-source-9",
                provider=ProviderKind.WEBHOOK,
            ),
            query={"payload": {"email": "maya@example.com"}},
        )
    )

    assert normalized_record.raw_record_id != ""
    assert normalized_record.status.value == "error"
    assert normalized_record.error.code == ErrorCode.MISSING_REQUIRED_FIELD.value
    assert normalized_record.normalized_data is None
