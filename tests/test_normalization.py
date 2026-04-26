"""Tests for saved-raw-record normalization."""

from __future__ import annotations

from backend.normalization import normalize_saved_raw_record
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind
from backend.schemas.storage import SavedRawRecord


def test_ipinfo_saved_record_normalizes_into_shared_shape() -> None:
    """IPinfo saved raw data should become the shared normalized shape."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-1",
        source_id="source-1",
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={
            "ip": "8.8.8.8",
            "org": "AS15169 Google LLC",
            "city": "Mountain View",
            "region": "California",
            "country": "US",
        },
        metadata={"mode": "live"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.provider == ProviderKind.IPINFO
    assert normalized_record.raw_record_id == "raw-1"
    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["ip_address"] == "8.8.8.8"
    assert normalized_record.normalized_data["organization"] == "AS15169 Google LLC"


def test_nominatim_search_saved_record_normalizes_into_shared_shape() -> None:
    """Nominatim search results should normalize into shared place data."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-2",
        source_id="source-2",
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        query="Indianapolis",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[
            {
                "display_name": "Indianapolis, Marion County, Indiana, United States",
                "lat": "39.7684",
                "lon": "-86.1581",
            }
        ],
        metadata={"mode": "search"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["places"][0]["display_name"].startswith("Indianapolis")
    assert normalized_record.normalized_data["places"][0]["latitude"] == 39.7684


def test_nominatim_reverse_saved_record_normalizes_into_shared_shape() -> None:
    """Nominatim reverse results should normalize into shared place data."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-3",
        source_id="source-3",
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        query={"lat": 39.7684, "lon": -86.1581},
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={
            "display_name": "Indianapolis, Marion County, Indiana, United States",
            "lat": "39.7684",
            "lon": "-86.1581",
        },
        metadata={"mode": "reverse"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["place"]["longitude"] == -86.1581


def test_crt_sh_saved_record_normalizes_into_shared_shape() -> None:
    """crt.sh certificate records should normalize into shared certificate data."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-crt-1",
        source_id="source-crt-1",
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[
            {
                "common_name": "example.com",
                "issuer_name": "Let's Encrypt",
                "not_before": "2026-01-10T00:00:00Z",
                "name_value": "*.example.com\nexample.com",
            }
        ],
        metadata={"mode": "search", "result_count": 1},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["certificates"][0]["common_name"] == "example.com"
    assert normalized_record.normalized_data["certificates"][0]["issuer_name"] == "Let's Encrypt"
    assert normalized_record.normalized_data["certificates"][0]["name_value"] == "*.example.com\nexample.com"


def test_crt_sh_no_results_normalizes_into_empty_certificates() -> None:
    """Empty crt.sh results should stay clean and become an empty certificates list."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-crt-2",
        source_id="source-crt-2",
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.NO_RESULTS,
        raw_data=[],
        metadata={"mode": "search", "result_count": 0},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.NO_RESULTS
    assert normalized_record.error is None
    assert normalized_record.normalized_data == {"certificates": []}


def test_crt_sh_normalization_returns_error_for_wrong_top_level_shape() -> None:
    """crt.sh normalization should fail cleanly when raw data is not a list."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-crt-3",
        source_id="source-crt-3",
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"common_name": "example.com"},
        metadata={"mode": "search"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


def test_crt_sh_normalization_returns_error_for_bad_certificate_item_type() -> None:
    """crt.sh normalization should fail cleanly when a certificate item is not a dict."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-crt-4",
        source_id="source-crt-4",
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[{"common_name": "example.com"}, "bad-item"],
        metadata={"mode": "search"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


def test_crt_sh_normalization_tolerates_missing_optional_name_value() -> None:
    """crt.sh normalization should keep working when name_value is missing."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-crt-5",
        source_id="source-crt-5",
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[
            {
                "common_name": "example.com",
                "issuer_name": "Let's Encrypt",
                "not_before": "2026-01-10T00:00:00Z",
            }
        ],
        metadata={"mode": "search"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert "name_value" not in normalized_record.normalized_data["certificates"][0]


def test_crt_sh_error_saved_record_passes_through_as_normalized_error() -> None:
    """Failed crt.sh raw records should stay failed after normalization."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-crt-6",
        source_id="source-crt-6",
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.ERROR,
        raw_data=None,
        error=ProviderError(
            code=ErrorCode.PROVIDER_TIMEOUT.value,
            message="Network request timed out.",
        ),
        metadata={"mode": "search"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.PROVIDER_TIMEOUT.value
    assert normalized_record.normalized_data is None


def test_error_saved_record_passes_through_as_normalized_error() -> None:
    """Provider error raw records should remain error-shaped after normalization."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-4",
        source_id="source-4",
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.ERROR,
        raw_data=None,
        error=ProviderError(
            code=ErrorCode.PROVIDER_TIMEOUT.value,
            message="Network request timed out.",
        ),
        metadata={"mode": "live"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error.code == ErrorCode.PROVIDER_TIMEOUT.value
    assert normalized_record.normalized_data is None


def test_normalization_router_returns_clean_error_for_unsupported_provider() -> None:
    """Providers without a normalizer should return a clean normalization error."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-5",
        source_id="source-5",
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"icao24": "abc123"},
        metadata={},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_UNSUPPORTED_PROVIDER.value
