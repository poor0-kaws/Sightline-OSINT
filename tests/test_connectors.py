"""Tests for the source adapter layer."""

import math

import pytest

import backend.connectors.api_connector as api_connector_module
from backend.connectors import build_preview_response
from backend.connectors import create_adapter
from backend.connectors import build_default_source_config
from backend.connectors import list_provider_definitions
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceRequest
from backend.schemas.ingestion import SourceKind
from backend.services.ingestion_service import IngestionService
from backend.utils.http_client import HTTPClientError
from backend.utils.http_client import JSONResponse


def test_provider_catalog_matches_architecture_note() -> None:
    """The provider list should match the architecture section."""
    definitions = list_provider_definitions()
    actual_providers = {definition.provider for definition in definitions}

    assert actual_providers == {
        ProviderKind.IPINFO,
        ProviderKind.CRT_SH,
        ProviderKind.OPENSKY,
        ProviderKind.NOMINATIM,
        ProviderKind.WEBHOOK,
        ProviderKind.CSV_UPLOAD,
        ProviderKind.MANUAL_INPUT,
    }


def test_ipinfo_happy_path_returns_shared_raw_wrapper() -> None:
    """A successful provider call should use the shared outer shape."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO),
            query="8.8.8.8",
        )
    )

    assert response.provider == ProviderKind.IPINFO
    assert response.source_type == SourceKind.API
    assert response.status == FetchStatus.SUCCESS
    assert response.raw_data["ip"] == "8.8.8.8"
    assert response.error is None


def test_ipinfo_rejects_invalid_ipv4_address() -> None:
    """IPinfo should reject values that are not real IPv4 addresses."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO),
            query="999.1.1.1",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_ipinfo_rejects_non_string_query_without_crashing() -> None:
    """IPinfo should return a clean error for non-string input."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO),
            query={"ip": "8.8.8.8"},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_empty_query_returns_provider_error_wrapper() -> None:
    """Blank input should fail at the source layer."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH),
            query="   ",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.raw_data is None
    assert response.error.code == "empty_query"


def test_opensky_accepts_bounding_box_queries() -> None:
    """OpenSky should accept bounding box input and return a wrapped response."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY),
            query={"lamin": 39.0, "lamax": 40.0, "lomin": -87.0, "lomax": -86.0},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None


def test_opensky_rejects_bounding_box_with_reversed_latitude_range() -> None:
    """OpenSky should reject impossible bounding boxes."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY),
            query={"lamin": 40.0, "lamax": 39.0, "lomin": -87.0, "lomax": -86.0},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_opensky_rejects_zero_area_bounding_box() -> None:
    """OpenSky should reject a bounding box that has no area."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY),
            query={"lamin": 39.0, "lamax": 39.0, "lomin": -87.0, "lomax": -86.0},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_opensky_rejects_aircraft_id_with_spaces() -> None:
    """OpenSky should reject aircraft ids that contain spaces."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY),
            query="AAL 123",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_opensky_preview_response_uses_stable_example_data() -> None:
    """OpenSky previews should stay readable without hitting the network."""
    response = build_preview_response(ProviderKind.OPENSKY)

    assert response.provider == ProviderKind.OPENSKY
    assert response.status == FetchStatus.SUCCESS
    assert response.metadata["mode"] == "preview"
    assert response.raw_data["states"][0][1] == "AAL123"


def test_webhook_missing_required_fields_returns_clear_error() -> None:
    """Webhook input should surface provider-level validation errors clearly."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.WEBHOOK),
            query={"payload": {"email": "maya@example.com"}},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "missing_required_field"


def test_csv_upload_preserves_original_rows() -> None:
    """CSV upload should keep the raw rows unchanged."""
    original_rows = [
        {"name": "Maya Patel", "email": "maya@example.com"},
        {"name": "Omar Ruiz", "email": "omar@example.com"},
    ]
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CSV_UPLOAD),
            query=original_rows,
        )
    )

    assert response.status == FetchStatus.SUCCESS
    assert response.raw_data == original_rows
    assert response.metadata["row_count"] == 2


def test_manual_input_requires_note_field() -> None:
    """Manual input should reject incomplete hand-entered records."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.MANUAL_INPUT),
            query={"person_name": "Maya Patel"},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "missing_required_field"


def test_plain_config_with_none_fields_gets_safe_defaults() -> None:
    """Plain config objects with None fields should still build an adapter."""

    class PartialConfig:
        source_id = None
        provider = "csv_upload"
        location = None
        display_name = None
        timeout_seconds = None

    adapter = create_adapter(PartialConfig())

    assert adapter.source_config.source_id == "csv_upload-source"
    assert adapter.source_config.location == "upload://case-import.csv"
    assert adapter.source_config.display_name == "CSV Upload"


def test_build_default_source_config_uses_timeout_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default source configs should inherit the app timeout setting."""
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "45")

    source_config = build_default_source_config(ProviderKind.IPINFO)

    assert source_config.timeout_seconds == 45


def test_create_adapter_uses_timeout_from_settings_when_config_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adapters should fall back to the settings timeout when config is blank."""
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "55")

    class PartialConfig:
        source_id = "ipinfo-source"
        provider = "ipinfo"
        location = ""
        display_name = ""
        timeout_seconds = None

    adapter = create_adapter(PartialConfig())

    assert adapter.source_config.timeout_seconds == 55


def test_preview_response_uses_provider_example_query() -> None:
    """Preview responses should be real examples, not empty placeholders."""
    response = build_preview_response(ProviderKind.NOMINATIM)

    assert response.provider == ProviderKind.NOMINATIM
    assert response.status == FetchStatus.SUCCESS
    assert response.raw_data[0]["display_name"].startswith("Indianapolis")


def test_crt_sh_rejects_invalid_domain_name() -> None:
    """crt.sh should reject domain strings with invalid label characters."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH),
            query="bad domain.com",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_crt_sh_rejects_url_like_value() -> None:
    """crt.sh should reject full URLs instead of plain domains."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH),
            query="https://example.com",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_crt_sh_rejects_ip_address_query() -> None:
    """crt.sh should reject IP addresses instead of plain domains."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH),
            query="8.8.8.8",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_nominatim_rejects_out_of_range_coordinates() -> None:
    """Nominatim should reject coordinates outside the earth range."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.NOMINATIM),
            query={"lat": 120, "lon": -86.1},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_nominatim_rejects_nan_coordinates() -> None:
    """Nominatim should reject NaN coordinates safely."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.NOMINATIM),
            query={"lat": math.nan, "lon": -86.1},
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


def test_nominatim_rejects_place_name_with_control_characters() -> None:
    """Nominatim should reject malformed place-name strings."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.NOMINATIM),
            query="Indianapolis\nIndiana",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error.code == "bad_query_type"


@pytest.mark.parametrize(
    ("provider", "query"),
    [
        (ProviderKind.IPINFO, object()),
        (ProviderKind.IPINFO, ["8.8.8.8"]),
        (ProviderKind.CRT_SH, {"domain": "example.com"}),
        (ProviderKind.CRT_SH, ["example.com"]),
        (ProviderKind.OPENSKY, {"lamin": "north"}),
        (ProviderKind.OPENSKY, math.nan),
        (ProviderKind.NOMINATIM, {"lat": "north", "lon": "west"}),
        (ProviderKind.NOMINATIM, []),
    ],
)
def test_run_source_request_returns_clean_error_for_malformed_queries(
    provider: ProviderKind,
    query: object,
) -> None:
    """Malformed provider inputs should produce errors instead of exceptions."""
    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=provider),
            query=query,
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None


def test_ipinfo_uses_live_http_path_when_api_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IPinfo should use the HTTP helper when a live key is present."""
    monkeypatch.setenv("IPINFO_API_KEY", "secret-key")

    captured_call: dict[str, object] = {}

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        captured_call["url"] = url
        captured_call["params"] = params
        captured_call["headers"] = headers
        captured_call["timeout_seconds"] = timeout_seconds
        return JSONResponse(
            status_code=200,
            data={
                "ip": "8.8.8.8",
                "city": "Mountain View",
                "region": "California",
                "country": "US",
                "org": "AS15169 Google LLC",
            },
            url="https://ipinfo.io/8.8.8.8/json?token=secret-key",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO, timeout_seconds=11),
            query="8.8.8.8",
        )
    )

    assert captured_call["url"] == "https://ipinfo.io/8.8.8.8/json"
    assert captured_call["params"] == {"token": "secret-key"}
    assert captured_call["headers"] == {"Accept": "application/json"}
    assert captured_call["timeout_seconds"] == 11
    assert response.status == FetchStatus.SUCCESS
    assert response.raw_data["ip"] == "8.8.8.8"
    assert response.metadata["mode"] == "live"


def test_ipinfo_returns_clean_error_when_http_helper_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live IPinfo failures should come back as provider errors, not crashes."""
    monkeypatch.setenv("IPINFO_API_KEY", "secret-key")

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        raise HTTPClientError("HTTP request failed with status 429.", status_code=429)

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.IPINFO),
            query="8.8.8.8",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None
    assert response.error.code == "provider_rate_limited"
    assert response.metadata["response_code"] == 429


def test_nominatim_uses_live_search_http_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nominatim place lookups should go through the live search endpoint."""
    captured_call: dict[str, object] = {}

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        captured_call["url"] = url
        captured_call["params"] = params
        captured_call["headers"] = headers
        captured_call["timeout_seconds"] = timeout_seconds
        return JSONResponse(
            status_code=200,
            data=[
                {
                    "display_name": "Indianapolis, Marion County, Indiana, United States",
                    "lat": "39.7684",
                    "lon": "-86.1581",
                }
            ],
            url="https://nominatim.openstreetmap.org/search?format=jsonv2&q=Indianapolis",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.NOMINATIM, timeout_seconds=12),
            query="Indianapolis",
        )
    )

    assert captured_call["url"] == "https://nominatim.openstreetmap.org/search"
    assert captured_call["params"] == {"format": "jsonv2", "q": "Indianapolis"}
    assert captured_call["headers"] == {"Accept": "application/json"}
    assert captured_call["timeout_seconds"] == 12
    assert response.status == FetchStatus.SUCCESS
    assert response.metadata["mode"] == "search"
    assert response.raw_data[0]["display_name"].startswith("Indianapolis")


def test_nominatim_uses_live_reverse_http_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nominatim coordinate lookups should go through the live reverse endpoint."""
    captured_call: dict[str, object] = {}

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        captured_call["url"] = url
        captured_call["params"] = params
        captured_call["headers"] = headers
        captured_call["timeout_seconds"] = timeout_seconds
        return JSONResponse(
            status_code=200,
            data={
                "display_name": "Indianapolis, Marion County, Indiana, United States",
                "lat": "39.7684",
                "lon": "-86.1581",
            },
            url="https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=39.7684&lon=-86.1581",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.NOMINATIM, timeout_seconds=13),
            query={"lat": 39.7684, "lon": -86.1581},
        )
    )

    assert captured_call["url"] == "https://nominatim.openstreetmap.org/reverse"
    assert captured_call["params"] == {
        "format": "jsonv2",
        "lat": 39.7684,
        "lon": -86.1581,
    }
    assert captured_call["headers"] == {"Accept": "application/json"}
    assert captured_call["timeout_seconds"] == 13
    assert response.status == FetchStatus.SUCCESS
    assert response.metadata["mode"] == "reverse"
    assert response.raw_data["display_name"].startswith("Indianapolis")


def test_nominatim_returns_clean_timeout_error_when_http_helper_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live Nominatim failures should return shared timeout errors, not crash."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        raise HTTPClientError("Network request timed out.", failure_kind="timeout")

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.NOMINATIM),
            query="Indianapolis",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None
    assert response.error.code == "provider_timeout"
    assert response.metadata["mode"] == "search"


def test_nominatim_returns_clean_error_for_wrong_search_response_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live Nominatim should reject valid JSON that has the wrong top-level shape."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        return JSONResponse(
            status_code=200,
            data={"display_name": "Indianapolis"},
            url="https://nominatim.openstreetmap.org/search?format=jsonv2&q=Indianapolis",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.NOMINATIM),
            query="Indianapolis",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None
    assert response.error.code == "provider_bad_response"
    assert response.metadata["mode"] == "search"


def test_crt_sh_uses_live_http_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CRT.sh domain lookups should go through the live search endpoint."""
    captured_call: dict[str, object] = {}

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        captured_call["url"] = url
        captured_call["params"] = params
        captured_call["headers"] = headers
        captured_call["timeout_seconds"] = timeout_seconds
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

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH, timeout_seconds=14),
            query="example.com",
        )
    )

    assert captured_call["url"] == "https://crt.sh"
    assert captured_call["params"] == {"q": "example.com", "output": "json"}
    assert captured_call["headers"] == {"Accept": "application/json"}
    assert captured_call["timeout_seconds"] == 14
    assert response.status == FetchStatus.SUCCESS
    assert response.metadata["mode"] == "search"
    assert response.metadata["result_count"] == 1
    assert response.raw_data[0]["common_name"] == "example.com"


def test_crt_sh_returns_no_results_for_empty_live_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CRT.sh should surface an empty result list as no_results."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        return JSONResponse(
            status_code=200,
            data=[],
            url="https://crt.sh?q=example.com&output=json",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH),
            query="example.com",
        )
    )

    assert response.status == FetchStatus.NO_RESULTS
    assert response.error is None
    assert response.raw_data == []
    assert response.metadata["result_count"] == 0


def test_crt_sh_returns_clean_timeout_error_when_http_helper_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live CRT.sh failures should return shared timeout errors, not crash."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        raise HTTPClientError("Network request timed out.", failure_kind="timeout")

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH),
            query="example.com",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None
    assert response.error.code == "provider_timeout"
    assert response.metadata["mode"] == "search"


def test_crt_sh_returns_clean_error_for_wrong_live_response_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live CRT.sh should reject valid JSON that has the wrong top-level shape."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        return JSONResponse(
            status_code=200,
            data={"common_name": "example.com"},
            url="https://crt.sh?q=example.com&output=json",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.CRT_SH),
            query="example.com",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None
    assert response.error.code == "provider_bad_response"
    assert response.metadata["mode"] == "search"


def test_opensky_uses_live_aircraft_http_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenSky aircraft lookups should use the live states endpoint."""
    captured_call: dict[str, object] = {}

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        captured_call["url"] = url
        captured_call["params"] = params
        captured_call["headers"] = headers
        captured_call["timeout_seconds"] = timeout_seconds
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

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY, timeout_seconds=15),
            query="AAL123",
        )
    )

    assert captured_call["url"] == "https://opensky-network.org/api/states/all"
    assert captured_call["params"] == {"icao24": "aal123"}
    assert captured_call["headers"] == {"Accept": "application/json"}
    assert captured_call["timeout_seconds"] == 15
    assert response.status == FetchStatus.SUCCESS
    assert response.metadata["mode"] == "aircraft"
    assert response.metadata["state_count"] == 1
    assert response.raw_data["states"][0][0] == "abc123"


def test_opensky_uses_live_bounds_http_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenSky bounding-box lookups should use the live states endpoint with bounds."""
    captured_call: dict[str, object] = {}

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        captured_call["url"] = url
        captured_call["params"] = params
        captured_call["headers"] = headers
        captured_call["timeout_seconds"] = timeout_seconds
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
            url="https://opensky-network.org/api/states/all?lamin=39.0&lamax=40.0&lomin=-87.0&lomax=-86.0",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY, timeout_seconds=16),
            query={"lamin": 39.0, "lamax": 40.0, "lomin": -87.0, "lomax": -86.0},
        )
    )

    assert captured_call["url"] == "https://opensky-network.org/api/states/all"
    assert captured_call["params"] == {
        "lamin": 39.0,
        "lamax": 40.0,
        "lomin": -87.0,
        "lomax": -86.0,
    }
    assert captured_call["headers"] == {"Accept": "application/json"}
    assert captured_call["timeout_seconds"] == 16
    assert response.status == FetchStatus.SUCCESS
    assert response.metadata["mode"] == "bounds"
    assert response.metadata["state_count"] == 1
    assert response.raw_data["states"][0][1] == "AAL123"


def test_opensky_returns_no_results_for_empty_live_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenSky should surface an empty states list as no_results."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        return JSONResponse(
            status_code=200,
            data={"time": 1_777_090_400, "states": []},
            url="https://opensky-network.org/api/states/all?icao24=aal123",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY),
            query="AAL123",
        )
    )

    assert response.status == FetchStatus.NO_RESULTS
    assert response.error is None
    assert response.metadata["state_count"] == 0


def test_opensky_returns_clean_timeout_error_when_http_helper_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live OpenSky failures should return shared timeout errors, not crash."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        raise HTTPClientError("Network request timed out.", failure_kind="timeout")

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY),
            query="AAL123",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None
    assert response.error.code == "provider_timeout"
    assert response.metadata["mode"] == "aircraft"


def test_opensky_returns_clean_error_for_wrong_live_response_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live OpenSky should reject valid JSON that has the wrong top-level shape."""

    def fake_get_json(url, *, params=None, headers=None, timeout_seconds=30, opener=None):
        return JSONResponse(
            status_code=200,
            data={"time": 1_777_090_400, "states": "not-a-list"},
            url="https://opensky-network.org/api/states/all?icao24=aal123",
        )

    monkeypatch.setattr(api_connector_module, "get_json", fake_get_json)

    service = IngestionService()
    response = service.run_source_request(
        SourceRequest(
            source=SourceConfig(provider=ProviderKind.OPENSKY),
            query="AAL123",
        )
    )

    assert response.status == FetchStatus.ERROR
    assert response.error is not None
    assert response.error.code == "provider_bad_response"
    assert response.metadata["mode"] == "aircraft"
