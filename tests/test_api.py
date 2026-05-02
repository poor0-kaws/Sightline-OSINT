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
    assert "/source/full" in response.json()["routes"]
    assert "/app" in response.json()["routes"]


def test_api_auth_token_protects_non_public_routes(tmp_path: object) -> None:
    """When a token is configured, API callers must send it."""
    app = build_app(settings=Settings(api_auth_token="secret-token", audit_log_path=str(tmp_path)))

    missing_token_response = _request(app, "GET", "/providers")
    valid_token_response = _request(
        app,
        "GET",
        "/providers",
        headers={"authorization": "Bearer secret-token"},
    )

    assert missing_token_response.status_code == 401
    assert valid_token_response.status_code == 200


def test_api_rejects_requests_over_size_limit(tmp_path: object) -> None:
    """Oversized JSON bodies should fail before route logic runs."""
    app = build_app(settings=Settings(max_request_bytes=5, audit_log_path=str(tmp_path)))

    response = _request(
        app,
        "POST",
        "/source/raw",
        json_body={"source": {"provider": "manual_input"}, "query": {"note": "too large"}},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_api_rate_limiter_returns_429_after_limit(tmp_path: object) -> None:
    """A client that exceeds the simple minute limit should get a clean 429."""
    app = build_app(settings=Settings(rate_limit_per_minute=1, audit_log_path=str(tmp_path)))

    first_response = _request(app, "GET", "/providers")
    second_response = _request(app, "GET", "/providers")

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["error"]["code"] == "rate_limited"


def test_api_writes_audit_log_events(tmp_path: object) -> None:
    """API requests should append simple JSONL audit events."""
    audit_log_path = tmp_path / "audit.log"
    app = build_app(settings=Settings(audit_log_path=str(audit_log_path)))

    response = _request(app, "GET", "/health")

    audit_lines = audit_log_path.read_text(encoding="utf-8").splitlines()
    assert response.status_code == 200
    assert len(audit_lines) == 1
    assert json.loads(audit_lines[0])["path"] == "/health"


def test_frontend_route_serves_the_graph_workspace_html() -> None:
    """The frontend should load as a real HTML page."""
    response = _request(build_app(), "GET", "/app")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sightline Fusion" in response.text
    assert 'id="root"' in response.text
    assert "/app/assets/app.js" in response.text


def test_frontend_graph_data_route_returns_empty_real_graph(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph data should start empty when no raw records have been saved."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(build_app(), "GET", "/app/graph-data")

    payload = response.json()
    assert response.status_code == 200
    assert payload["title"].endswith("Graph Workspace")
    assert payload["case"]["status"] == "EMPTY"
    assert payload["nodes"] == []
    assert payload["edges"] == []
    assert any(item["label"] == "Person" for item in payload["legend"])
    assert payload["activity"][0]["text"] == "No saved raw records are available yet."


def test_frontend_graph_data_route_builds_graph_from_saved_raw_records(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph data should be generated from saved raw records, not demo data."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    app = build_app()

    _request(
        app,
        "POST",
        "/source/raw",
        json_body={
            "source": {
                "source_id": "api-graph-case",
                "provider": "manual_input",
                "source_kind": "manual",
            },
            "query": {
                "note": "Analyst note about Alice Ng",
                "full_name": "Alice Ng",
                "email": "alice@personalmail.org",
                "phone": "+1 (317) 555-0101",
                "company_name": "OpenAI LLC",
            },
        },
    )

    response = _request(app, "GET", "/app/graph-data")
    payload = response.json()
    node_types = {node["type"] for node in payload["nodes"]}
    node_labels = {node["label"] for node in payload["nodes"]}
    edge_labels = {edge["label"] for edge in payload["edges"]}

    assert response.status_code == 200
    assert payload["case"]["status"] == "ACTIVE"
    assert {"person", "email", "phone", "organization"}.issubset(node_types)
    assert "Alice Ng" in node_labels
    assert {"person uses email", "person uses phone", "person associated with company"}.issubset(edge_labels)
    assert all(not node["id"].startswith("person-alice") for node in payload["nodes"])


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


def test_source_resolution_endpoint_saves_normalizes_and_returns_resolution(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source resolution should ingest one record and return the current batch resolution."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(
        build_app(),
        "POST",
        "/source/resolution",
        json_body={
            "source": {
                "source_id": "api-resolution-case",
                "provider": "manual_input",
                "source_kind": "manual",
            },
            "query": {
                "note": "Analyst note about Alice Ng",
                "full_name": "Alice Ng",
                "email": "alice@example.org",
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["record"]["status"] == "success"
    assert payload["resolution"]["source_record_count"] == 1
    assert payload["resolution"]["candidate_count"] == 1


def test_source_full_endpoint_returns_all_pipeline_outputs(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full source endpoint should run the whole pipeline once."""
    from backend.graph import InMemoryGraphRepository

    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    repository = InMemoryGraphRepository()
    app = build_app(graph_repository=repository)

    response = _request(
        app,
        "POST",
        "/source/full",
        json_body={
            "source": {
                "case_id": "case-full",
                "source_id": "api-full-case",
                "provider": "manual_input",
                "source_kind": "manual",
            },
            "query": {
                "note": "Analyst note about Alice Ng",
                "full_name": "Alice Ng",
                "email": "alice@example.org",
                "phone": "+1 (317) 555-0101",
            },
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["record"]["case_id"] == "case-full"
    assert payload["relationships"]["status"] == "success"
    assert payload["graph_write"]["status"] == "success"
    assert payload["graph"]["nodes"] != []


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


def test_resolution_matches_endpoint_compares_saved_raw_records(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolution endpoint should compare candidates built from saved raw records."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    app = build_app()

    _request(
        app,
        "POST",
        "/source/raw",
        json_body={
            "source": {"source_id": "resolution-1", "provider": "manual_input", "source_kind": "manual"},
            "query": {
                "note": "Manual lead",
                "full_name": "Maya Patel",
                "email": "maya.patel@gmail.com",
                "phone": "3175550101",
                "company_name": "OpenAI LLC",
            },
        },
    )
    _request(
        app,
        "POST",
        "/source/raw",
        json_body={
            "source": {"source_id": "resolution-2", "provider": "webhook", "source_kind": "webhook"},
            "query": {
                "event_type": "lead.created",
                "payload": {
                    "full_name": "Maya Patel",
                    "email": "maya.patel@gmail.com",
                    "phone": "+1 (317) 555-0101",
                    "company_name": "OpenAI",
                },
            },
        },
    )

    response = _request(app, "GET", "/resolution/matches")
    resolution = response.json()["resolution"]

    assert response.status_code == 200
    assert resolution["candidate_count"] == 2
    assert resolution["comparison_count"] == 1
    assert resolution["summary"]["merge"] == 1


def test_resolution_matches_endpoint_handles_empty_storage(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty storage should resolve to an empty batch, not an exception."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    response = _request(build_app(), "GET", "/resolution/matches")
    resolution = response.json()["resolution"]

    assert response.status_code == 200
    assert resolution["source_record_count"] == 0
    assert resolution["candidate_count"] == 0
    assert resolution["comparison_count"] == 0
    assert resolution["matches"] == []


def test_source_graph_endpoint_writes_to_injected_graph_repository(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph endpoint should run the full source-to-graph-write path."""
    from backend.graph import InMemoryGraphRepository

    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    repository = InMemoryGraphRepository()
    app = build_app(graph_repository=repository)

    response = _request(
        app,
        "POST",
        "/source/graph",
        json_body={
            "source": {"source_id": "graph-api-1", "provider": "manual_input", "source_kind": "manual"},
            "query": {
                "note": "Graph write lead",
                "full_name": "Alice Ng",
                "email": "alice@personalmail.org",
                "phone": "+1 (317) 555-0101",
                "company_name": "OpenAI LLC",
            },
        },
    )

    payload = response.json()["graph_write"]
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["nodes_written"] == 4
    assert payload["relationships_written"] == 3
    assert len(repository.nodes_by_key) == 4
    assert len(repository.relationships_by_key) == 3


def test_source_graph_endpoint_returns_clean_error_for_bad_source(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bad provider input should flow through as a graph write error wrapper."""
    from backend.graph import InMemoryGraphRepository

    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    repository = InMemoryGraphRepository()
    app = build_app(graph_repository=repository)

    response = _request(
        app,
        "POST",
        "/source/graph",
        json_body={
            "source": {"source_id": "graph-api-bad", "provider": "manual_input", "source_kind": "manual"},
            "query": {"full_name": "Missing Note"},
        },
    )

    payload = response.json()["graph_write"]
    assert response.status_code == 200
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "missing_required_field"
    assert payload["nodes_written"] == 0
    assert len(repository.nodes_by_key) == 0


def test_graph_rebuild_endpoint_replays_saved_raw_records_into_graph_repository(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph rebuild should write existing saved raw records to the repository."""
    from backend.graph import InMemoryGraphRepository

    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    repository = InMemoryGraphRepository()
    app = build_app(graph_repository=repository)

    _request(
        app,
        "POST",
        "/source/raw",
        json_body={
            "source": {"source_id": "graph-rebuild-1", "provider": "manual_input", "source_kind": "manual"},
            "query": {
                "note": "Rebuild lead",
                "full_name": "Alice Ng",
                "email": "alice@personalmail.org",
                "phone": "+1 (317) 555-0101",
                "company_name": "OpenAI LLC",
            },
        },
    )

    response = _request(app, "POST", "/graph/rebuild")
    rebuild = response.json()["graph_rebuild"]

    assert response.status_code == 200
    assert rebuild["status"] == "success"
    assert rebuild["saved_raw_record_count"] == 1
    assert rebuild["nodes_written"] == 4
    assert rebuild["relationships_written"] == 3
    assert len(repository.nodes_by_key) == 4


def test_graph_data_and_status_endpoints_read_repository(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph read endpoints should return repository data after a write."""
    from backend.graph import InMemoryGraphRepository

    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    repository = InMemoryGraphRepository()
    app = build_app(graph_repository=repository)

    _request(
        app,
        "POST",
        "/source/graph",
        json_body={
            "source": {
                "case_id": "case-graph",
                "source_id": "graph-read-1",
                "provider": "manual_input",
                "source_kind": "manual",
            },
            "query": {
                "note": "Graph read lead",
                "full_name": "Alice Ng",
                "email": "alice@personalmail.org",
            },
        },
    )

    graph_response = _request(app, "GET", "/graph/data?case_id=case-graph")
    status_response = _request(app, "GET", "/graph/status?case_id=case-graph")

    assert graph_response.status_code == 200
    assert graph_response.json()["graph"]["nodes"] != []
    assert status_response.json()["nodes"] == len(graph_response.json()["graph"]["nodes"])


def test_graph_rebuild_endpoint_handles_empty_storage(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Graph rebuild with no saved records should return zero counts."""
    from backend.graph import InMemoryGraphRepository

    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    repository = InMemoryGraphRepository()
    app = build_app(graph_repository=repository)

    response = _request(app, "POST", "/graph/rebuild")
    rebuild = response.json()["graph_rebuild"]

    assert response.status_code == 200
    assert rebuild["status"] == "success"
    assert rebuild["saved_raw_record_count"] == 0
    assert rebuild["nodes_written"] == 0
    assert rebuild["relationships_written"] == 0
    assert len(repository.nodes_by_key) == 0


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


def test_cases_endpoint_and_raw_records_filter_by_case(
    tmp_path: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cases should be derived from saved raw records and records should filter by case."""
    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))
    app = build_app()

    for case_id in ["case-alpha", "case-beta"]:
        _request(
            app,
            "POST",
            "/source/raw",
            json_body={
                "source": {
                    "case_id": case_id,
                    "source_id": f"{case_id}-source",
                    "provider": "manual_input",
                    "source_kind": "manual",
                },
                "query": {"note": f"Note for {case_id}", "full_name": "Alice Ng"},
            },
        )

    cases_response = _request(app, "GET", "/cases")
    filtered_response = _request(app, "GET", "/records/raw?case_id=case-alpha")

    assert cases_response.status_code == 200
    assert {case["case_id"] for case in cases_response.json()["cases"]} == {"case-alpha", "case-beta"}
    assert len(filtered_response.json()["records"]) == 1
    assert filtered_response.json()["records"][0]["case_id"] == "case-alpha"


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
