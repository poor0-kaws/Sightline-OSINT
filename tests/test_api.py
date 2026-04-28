"""Tests for the small HTTP API layer."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from backend.api import build_app
from backend.schemas.ingestion import ProviderKind
from backend.settings import Settings
from backend.services.ingestion_service import IngestionService


def test_health_endpoint_returns_basic_app_state(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Health should show the app name, env, and storage location."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(
        build_app(),
        "GET",
        "/health",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["raw_storage_path"] == str(tmp_path)


def test_root_endpoint_lists_available_routes() -> None:
    """Root should work like a tiny map of the current API."""
    response = _request(build_app(), "GET", "/")

    assert response.status_code == 200
    assert "/source/normalized" in response.json()["routes"]


def test_providers_endpoint_lists_supported_providers() -> None:
    """Providers should return the current provider definitions."""
    response = _request(build_app(), "GET", "/providers")

    assert response.status_code == 200
    assert any(provider["provider"] == "ipinfo" for provider in response.json()["providers"])


def test_provider_preview_endpoint_returns_shared_preview_shape() -> None:
    """Preview should return one sample raw response for the requested provider."""
    response = _request(build_app(), "GET", "/providers/ipinfo/preview")

    assert response.status_code == 200
    assert response.json()["preview"]["provider"] == "ipinfo"


def test_provider_preview_endpoint_rejects_unknown_provider() -> None:
    """Bad provider path params should fail early with a 400."""
    response = _request(build_app(), "GET", "/providers/not-real/preview")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_provider"


def test_source_raw_endpoint_saves_raw_response_and_returns_record_id(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw endpoint should hit the real ingestion service and save the response."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(
        build_app(),
        "POST",
        "/source/raw",
        json_body={
            "source": {
                "source_id": "api-case-1",
                "provider": "webhook",
                "source_kind": "webhook",
            },
            "query": {
                "event_type": "breach.alert",
                "payload": {"email": "maya@example.com", "domain": "example.com"},
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["response"]["status"] == "success"
    assert payload["saved_raw_record_id"] != ""


def test_source_normalized_endpoint_returns_enriched_normalized_record(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalized endpoint should return provider-shaped and shared extracted data."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(
        build_app(),
        "POST",
        "/source/normalized",
        json_body={
            "source": {
                "source_id": "api-case-2",
                "provider": "manual_input",
                "source_kind": "manual",
            },
            "query": {
                "note": "Analyst note about Alice Ng",
                "full_name": "Alice Ng",
                "email": "alice@example.org",
                "company_name": "OpenAI LLC",
            },
        },
    )

    payload = response.json()["record"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["normalized_data"]["fields"]["full_name"] == "Alice Ng"
    assert any(entity["entity_type"] == "person" for entity in payload["entities"])


def test_source_relationships_endpoint_returns_graph_ready_edges(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Relationships endpoint should run the whole pipeline through edge extraction."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(
        build_app(),
        "POST",
        "/source/relationships",
        json_body={
            "source": {
                "source_id": "api-case-3",
                "provider": "manual_input",
                "source_kind": "manual",
            },
            "query": {
                "note": "Analyst note about Alice Ng",
                "full_name": "Alice Ng",
                "emails": ["alice@example.org", "support@example.org"],
                "phone_numbers": ["3175550101", "1234567890"],
                "company_name": "OpenAI LLC",
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["relationships"]["status"] == "success"
    assert [relationship["relationship_type"] for relationship in payload["relationships"]["relationships"]] == [
        "person_uses_email",
        "person_uses_phone",
        "person_associated_with_company",
    ]


def test_records_endpoints_list_and_load_saved_raw_records(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw-record endpoints should show what the ingestion service saved."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    app = build_app()

    create_response = _request(
        app,
        "POST",
        "/source/raw",
        json_body={
            "source": {
                "source_id": "api-case-4",
                "provider": "manual_input",
                "source_kind": "manual",
            },
            "query": {"note": "Possible link", "domain": "portal.example.com"},
        },
    )
    record_id = create_response.json()["saved_raw_record_id"]

    list_response = _request(app, "GET", "/records/raw")
    load_response = _request(app, "GET", f"/records/raw/{record_id}")

    assert list_response.status_code == 200
    assert any(record["record_id"] == record_id for record in list_response.json()["records"])
    assert load_response.status_code == 200
    assert load_response.json()["record"]["record_id"] == record_id


def test_load_raw_record_endpoint_returns_404_for_unknown_id(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown raw record ids should return a clean 404 response."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(build_app(), "GET", "/records/raw/not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "raw_record_not_found"


def test_source_endpoint_rejects_missing_source_field() -> None:
    """The API should reject malformed request bodies before the service layer runs."""
    response = _request(
        build_app(),
        "POST",
        "/source/raw",
        json_body={"query": "8.8.8.8"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_source"


def test_source_endpoint_rejects_bad_source_kind() -> None:
    """Bad source kind values should fail early and clearly."""
    response = _request(
        build_app(),
        "POST",
        "/source/raw",
        json_body={
            "source": {"provider": "ipinfo", "source_kind": "not-real"},
            "query": "8.8.8.8",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_source_kind"


def test_source_endpoint_rejects_bad_timeout() -> None:
    """Timeout must be a real positive integer."""
    response = _request(
        build_app(),
        "POST",
        "/source/raw",
        json_body={
            "source": {"provider": "ipinfo", "timeout_seconds": 0},
            "query": "8.8.8.8",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_timeout"


def test_source_endpoint_rejects_bad_provider() -> None:
    """Bad provider values should fail before hitting the connectors layer."""
    response = _request(
        build_app(),
        "POST",
        "/source/raw",
        json_body={
            "source": {"provider": "not-real"},
            "query": "8.8.8.8",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_provider"


def test_source_endpoint_rejects_malformed_json() -> None:
    """Malformed JSON should return a clean 400 instead of a server crash."""
    response = _request(
        build_app(),
        "POST",
        "/source/raw",
        raw_body=b"{not-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_json"


def test_api_returns_500_when_handler_raises_unexpected_error() -> None:
    """Unexpected server crashes should become a clean 500 response."""

    class BrokenIngestionService(IngestionService):
        def list_supported_providers(self) -> list[object]:
            raise RuntimeError("boom")

    response = _request(
        build_app(ingestion_service=BrokenIngestionService()),
        "GET",
        "/providers",
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"


def _request(
    app: object,
    method: str,
    path: str,
    *,
    json_body: object | None = None,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Send one real in-memory HTTP request to the ASGI app."""
    return asyncio.run(
        _async_request(
            app,
            method,
            path,
            json_body=json_body,
            raw_body=raw_body,
            headers=headers,
        )
    )


async def _async_request(
    app: object,
    method: str,
    path: str,
    *,
    json_body: object | None = None,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Run one request through httpx ASGI transport."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        if json_body is not None:
            return await client.request(method, path, json=json_body, headers=headers)

        if raw_body is not None:
            return await client.request(method, path, content=raw_body, headers=headers)

        return await client.request(method, path, headers=headers)
