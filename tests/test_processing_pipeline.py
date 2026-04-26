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
