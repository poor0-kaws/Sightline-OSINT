"""Tests for the source adapter layer."""

import math

import pytest

from backend.connectors import build_preview_response
from backend.connectors import create_adapter
from backend.connectors import list_provider_definitions
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceRequest
from backend.schemas.ingestion import SourceKind
from backend.services.ingestion_service import IngestionService


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

    assert response.status == FetchStatus.PARTIAL_SUCCESS
    assert response.raw_data["bounds"]["lamin"] == 39.0


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
