"""Tests for file-based raw storage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import RawProviderResponse
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceKind
from backend.storage.raw_storage_repository import FileRawStorageRepository
from backend.storage.raw_storage_repository import list_raw_responses
from backend.storage.raw_storage_repository import load_raw_response
from backend.storage.raw_storage_repository import save_raw_response
from backend.storage.raw_storage_repository import save_raw_response_safely


def test_save_raw_response_writes_json_file(tmp_path: object) -> None:
    """Saving a raw response should create one JSON file on disk."""
    repository = FileRawStorageRepository(tmp_path)
    source_config = SourceConfig(source_id="source-123", provider=ProviderKind.IPINFO)
    raw_response = RawProviderResponse(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-25T12:00:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"ip": "8.8.8.8"},
        metadata={"response_code": 200},
    )

    saved_record = repository.save_raw_response(source_config=source_config, raw_response=raw_response)

    saved_files = list(tmp_path.glob("*.json"))

    assert saved_record.source_id == "source-123"
    assert saved_record.query == "8.8.8.8"
    assert saved_record.fetched_at == "2026-04-25T12:00:00+00:00"
    assert len(saved_files) == 1

    saved_file_contents = json.loads(saved_files[0].read_text(encoding="utf-8"))

    assert saved_file_contents["provider"] == "ipinfo"
    assert saved_file_contents["source_id"] == "source-123"
    assert saved_file_contents["query"] == "8.8.8.8"
    assert saved_file_contents["raw_data"]["ip"] == "8.8.8.8"


def test_save_raw_response_preserves_error_details(tmp_path: object) -> None:
    """Saving an error response should keep the provider error data."""
    repository = FileRawStorageRepository(tmp_path)
    source_config = SourceConfig(source_id="source-456", provider=ProviderKind.CRT_SH)
    raw_response = RawProviderResponse(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="bad domain",
        fetched_at="2026-04-25T12:00:00+00:00",
        status=FetchStatus.ERROR,
        raw_data=None,
        error=ProviderError(code="bad_query_type", message="crt.sh expects a domain like example.com."),
        metadata={"location": "https://crt.sh"},
    )

    repository.save_raw_response(source_config=source_config, raw_response=raw_response)

    saved_files = list(tmp_path.glob("*.json"))
    saved_file_contents = json.loads(saved_files[0].read_text(encoding="utf-8"))

    assert saved_file_contents["status"] == "error"
    assert saved_file_contents["error"]["code"] == "bad_query_type"
    assert saved_file_contents["metadata"]["location"] == "https://crt.sh"


def test_load_raw_response_reads_saved_record_back(tmp_path: object) -> None:
    """Loading should rebuild the saved raw record from disk."""
    repository = FileRawStorageRepository(tmp_path)
    source_config = SourceConfig(source_id="source-789", provider=ProviderKind.WEBHOOK)
    raw_response = RawProviderResponse(
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        query={"event_type": "breach.alert", "payload": {"email": "maya@example.com"}},
        fetched_at="2026-04-25T12:10:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"event_type": "breach.alert", "payload": {"email": "maya@example.com"}},
        metadata={"delivery_id": "evt-123"},
    )

    saved_record = repository.save_raw_response(source_config=source_config, raw_response=raw_response)
    loaded_record = repository.load_raw_response(saved_record.record_id)

    assert loaded_record.record_id == saved_record.record_id
    assert loaded_record.provider == ProviderKind.WEBHOOK
    assert loaded_record.source_type == SourceKind.WEBHOOK
    assert loaded_record.metadata["delivery_id"] == "evt-123"


def test_list_raw_responses_returns_all_saved_records(tmp_path: object) -> None:
    """Listing should return every saved raw record from disk."""
    repository = FileRawStorageRepository(tmp_path)
    first_config = SourceConfig(source_id="source-a", provider=ProviderKind.IPINFO)
    second_config = SourceConfig(source_id="source-b", provider=ProviderKind.CSV_UPLOAD)
    first_response = RawProviderResponse(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-25T12:15:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"ip": "8.8.8.8"},
        metadata={"response_code": 200},
    )
    second_response = RawProviderResponse(
        provider=ProviderKind.CSV_UPLOAD,
        source_type=SourceKind.CSV,
        query=[{"name": "Maya Patel"}],
        fetched_at="2026-04-25T12:16:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[{"name": "Maya Patel"}],
        metadata={"row_count": 1},
    )

    repository.save_raw_response(source_config=first_config, raw_response=first_response)
    repository.save_raw_response(source_config=second_config, raw_response=second_response)
    saved_records = repository.list_raw_responses()

    assert len(saved_records) == 2
    assert {record.source_id for record in saved_records} == {"source-a", "source-b"}


def test_list_raw_responses_can_filter_by_case_id(tmp_path: object) -> None:
    """Case filtering should only return records from one investigation."""
    repository = FileRawStorageRepository(tmp_path)
    raw_response = RawProviderResponse(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-25T12:17:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"ip": "8.8.8.8"},
        metadata={},
    )

    repository.save_raw_response(
        source_config=SourceConfig(case_id="case-alpha", source_id="source-a", provider=ProviderKind.IPINFO),
        raw_response=raw_response,
    )
    repository.save_raw_response(
        source_config=SourceConfig(case_id="case-beta", source_id="source-b", provider=ProviderKind.IPINFO),
        raw_response=raw_response,
    )

    saved_records = repository.list_raw_responses(case_id="case-alpha")

    assert len(saved_records) == 1
    assert saved_records[0].case_id == "case-alpha"


def test_load_raw_response_requires_exact_full_record_id(tmp_path: Path) -> None:
    """Loading should not confuse two records that share the same id prefix."""
    repository = FileRawStorageRepository(tmp_path)

    first_payload = {
        "record_id": "abcdef12-first-full-id",
        "source_id": "source-one",
        "provider": "ipinfo",
        "source_type": "api",
        "query": "8.8.8.8",
        "fetched_at": "2026-04-25T12:20:00+00:00",
        "saved_at": "2026-04-25T12:21:00+00:00",
        "status": "success",
        "raw_data": {"ip": "8.8.8.8"},
        "error": None,
        "metadata": {},
    }
    second_payload = {
        "record_id": "abcdef12-second-full-id",
        "source_id": "source-two",
        "provider": "crt.sh",
        "source_type": "scraper",
        "query": "example.com",
        "fetched_at": "2026-04-25T12:22:00+00:00",
        "saved_at": "2026-04-25T12:23:00+00:00",
        "status": "success",
        "raw_data": [{"common_name": "example.com"}],
        "error": None,
        "metadata": {},
    }

    (tmp_path / "first.json").write_text(json.dumps(first_payload), encoding="utf-8")
    (tmp_path / "second.json").write_text(json.dumps(second_payload), encoding="utf-8")

    loaded_record = repository.load_raw_response("abcdef12-second-full-id")

    assert loaded_record.source_id == "source-two"
    assert loaded_record.provider == ProviderKind.CRT_SH


def test_load_raw_response_raises_for_missing_record_id(tmp_path: Path) -> None:
    """Loading should raise a clean file-not-found error for unknown ids."""
    repository = FileRawStorageRepository(tmp_path)

    with pytest.raises(FileNotFoundError):
        repository.load_raw_response("missing-record-id")


def test_list_raw_responses_skips_corrupt_json_files(tmp_path: Path) -> None:
    """One broken JSON file should not break listing the whole storage folder."""
    repository = FileRawStorageRepository(tmp_path)
    source_config = SourceConfig(source_id="source-ok", provider=ProviderKind.IPINFO)
    raw_response = RawProviderResponse(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-25T12:30:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"ip": "8.8.8.8"},
        metadata={"response_code": 200},
    )

    repository.save_raw_response(source_config=source_config, raw_response=raw_response)
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")

    saved_records = repository.list_raw_responses()

    assert len(saved_records) == 1
    assert saved_records[0].source_id == "source-ok"


def test_list_raw_responses_skips_invalid_saved_record_shape(tmp_path: Path) -> None:
    """A malformed saved-record payload should not break listing."""
    repository = FileRawStorageRepository(tmp_path)
    valid_payload = {
        "record_id": "valid-record-id",
        "source_id": "source-ok",
        "provider": "ipinfo",
        "source_type": "api",
        "query": "8.8.8.8",
        "fetched_at": "2026-04-25T12:31:00+00:00",
        "saved_at": "2026-04-25T12:32:00+00:00",
        "status": "success",
        "raw_data": {"ip": "8.8.8.8"},
        "error": None,
        "metadata": {},
    }

    (tmp_path / "good.json").write_text(json.dumps(valid_payload), encoding="utf-8")
    (tmp_path / "bad.json").write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    saved_records = repository.list_raw_responses()

    assert len(saved_records) == 1
    assert saved_records[0].record_id == "valid-record-id"


def test_load_raw_response_coerces_non_dict_metadata_safely(tmp_path: Path) -> None:
    """Odd metadata shapes should load without crashing."""
    repository = FileRawStorageRepository(tmp_path)
    payload = {
        "record_id": "metadata-record-id",
        "source_id": "source-meta",
        "provider": "webhook",
        "source_type": "webhook",
        "query": {"event_type": "breach.alert"},
        "fetched_at": "2026-04-25T12:33:00+00:00",
        "saved_at": "2026-04-25T12:34:00+00:00",
        "status": "success",
        "raw_data": {"event_type": "breach.alert"},
        "error": None,
        "metadata": ["unexpected", "list"],
    }

    (tmp_path / "metadata.json").write_text(json.dumps(payload), encoding="utf-8")

    loaded_record = repository.load_raw_response("metadata-record-id")

    assert loaded_record.metadata["raw_metadata"] == ["unexpected", "list"]


def test_save_raw_response_safely_returns_none_for_non_json_safe_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Safe save should swallow storage errors and return None."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    source_config = SourceConfig(source_id="source-safe", provider=ProviderKind.IPINFO)
    raw_response = RawProviderResponse(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-25T12:35:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"bad": {1, 2, 3}},
        metadata={},
    )

    result = save_raw_response_safely(source_config=source_config, raw_response=raw_response)

    assert result is None
    assert list(tmp_path.glob("*.json")) == []


def test_save_raw_response_does_not_leave_partial_file_on_serialization_failure(tmp_path: Path) -> None:
    """A failed save should not leave behind a corrupt partial JSON file."""
    repository = FileRawStorageRepository(tmp_path)
    source_config = SourceConfig(source_id="source-bad", provider=ProviderKind.IPINFO)
    raw_response = RawProviderResponse(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-25T12:36:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"bad": {1, 2, 3}},
        metadata={},
    )

    with pytest.raises(TypeError):
        repository.save_raw_response(source_config=source_config, raw_response=raw_response)

    assert list(tmp_path.glob("*.json")) == []
    assert list(tmp_path.glob("*.tmp")) == []


def test_default_storage_helpers_use_env_storage_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Top-level storage helpers should use the configured storage path."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    source_config = SourceConfig(source_id="source-default", provider=ProviderKind.IPINFO)
    raw_response = RawProviderResponse(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-25T12:40:00+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"ip": "8.8.8.8"},
        metadata={},
    )

    saved_record = save_raw_response(source_config=source_config, raw_response=raw_response)
    loaded_record = load_raw_response(saved_record.record_id)
    listed_records = list_raw_responses()

    assert loaded_record.record_id == saved_record.record_id
    assert len(listed_records) == 1
