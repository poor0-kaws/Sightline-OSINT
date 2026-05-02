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


def test_ipinfo_lite_saved_record_normalizes_into_shared_shape() -> None:
    """IPinfo Lite raw data should map into the same normalized IPinfo shape."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-ip-lite-1",
        source_id="source-ip-lite-1",
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={
            "ip": "8.8.8.8",
            "asn": "AS15169",
            "as_name": "Google LLC",
            "as_domain": "google.com",
            "country_code": "US",
            "country": "United States",
            "continent_code": "NA",
            "continent": "North America",
        },
        metadata={"mode": "live"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["ip_address"] == "8.8.8.8"
    assert normalized_record.normalized_data["organization"] == "AS15169 Google LLC"
    assert normalized_record.normalized_data["as_domain"] == "google.com"
    assert normalized_record.normalized_data["country"] == "United States"


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


def test_nominatim_search_normalization_returns_error_for_bad_item_type() -> None:
    """Nominatim search normalization should fail when one result item is not a dict."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-nom-1",
        source_id="source-nom-1",
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
            },
            "bad-item",
        ],
        metadata={"mode": "search"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


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


def test_opensky_aircraft_saved_record_normalizes_into_shared_shape() -> None:
    """OpenSky aircraft records should normalize into one aircraft object."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-open-1",
        source_id="source-open-1",
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        query="AAL123",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={
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
        metadata={"mode": "aircraft", "state_count": 1},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["aircraft"]["icao24"] == "abc123"
    assert normalized_record.normalized_data["aircraft"]["longitude"] == -86.1581


def test_opensky_bounds_saved_record_normalizes_into_shared_shape() -> None:
    """OpenSky bounds records should normalize into states plus bounds."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-open-2",
        source_id="source-open-2",
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        query={"lamin": 39.0, "lamax": 40.0, "lomin": -87.0, "lomax": -86.0},
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={
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
        metadata={"mode": "bounds", "state_count": 1},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["states"][0]["callsign"] == "AAL123"
    assert normalized_record.normalized_data["bounds"]["lamin"] == 39.0


def test_opensky_no_results_normalizes_into_empty_shared_payload() -> None:
    """Empty OpenSky results should become a clean no-results normalized record."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-open-3",
        source_id="source-open-3",
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        query={"lamin": 39.0, "lamax": 40.0, "lomin": -87.0, "lomax": -86.0},
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.NO_RESULTS,
        raw_data={"time": 1_777_090_400, "states": []},
        metadata={"mode": "bounds", "state_count": 0},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.NO_RESULTS
    assert normalized_record.error is None
    assert normalized_record.normalized_data["states"] == []
    assert normalized_record.normalized_data["bounds"]["lamin"] == 39.0


def test_opensky_normalization_returns_error_for_wrong_top_level_shape() -> None:
    """OpenSky normalization should fail cleanly when raw data is not a dict."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-open-4",
        source_id="source-open-4",
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        query="AAL123",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=["bad-top-level"],
        metadata={"mode": "aircraft"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


def test_opensky_normalization_returns_error_for_short_state_vector() -> None:
    """OpenSky normalization should fail when a state vector is too short."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-open-5",
        source_id="source-open-5",
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        query="AAL123",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"time": 1_777_090_400, "states": [["abc123", "AAL123"]]},
        metadata={"mode": "aircraft"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


def test_opensky_error_saved_record_passes_through_as_normalized_error() -> None:
    """Failed OpenSky raw records should stay failed after normalization."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-open-6",
        source_id="source-open-6",
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        query="AAL123",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.ERROR,
        raw_data=None,
        error=ProviderError(
            code=ErrorCode.PROVIDER_TIMEOUT.value,
            message="Network request timed out.",
        ),
        metadata={"mode": "aircraft"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.PROVIDER_TIMEOUT.value
    assert normalized_record.normalized_data is None


def test_webhook_saved_record_normalizes_into_shared_shape() -> None:
    """Webhook raw records should normalize into event type plus payload."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-web-1",
        source_id="source-web-1",
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        query={
            "event_type": "breach.alert",
            "payload": {"email": "maya@example.com", "domain": "example.com"},
        },
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={
            "event_type": "breach.alert",
            "payload": {"email": "maya@example.com", "domain": "example.com"},
        },
        metadata={"delivery_mode": "push"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["event_type"] == "breach.alert"
    assert normalized_record.normalized_data["payload"]["email"] == "maya@example.com"


def test_webhook_normalization_returns_error_for_non_dict_payload() -> None:
    """Webhook normalization should fail when payload is not a dictionary."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-web-2",
        source_id="source-web-2",
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        query={"event_type": "breach.alert", "payload": []},
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"event_type": "breach.alert", "payload": []},
        metadata={"delivery_mode": "push"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


def test_webhook_error_saved_record_passes_through_as_normalized_error() -> None:
    """Failed webhook raw records should stay failed after normalization."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-web-3",
        source_id="source-web-3",
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        query={"payload": {"email": "maya@example.com"}},
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.ERROR,
        raw_data=None,
        error=ProviderError(
            code=ErrorCode.MISSING_REQUIRED_FIELD.value,
            message="Webhook payload needs an event_type field.",
        ),
        metadata={"delivery_mode": "push"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.MISSING_REQUIRED_FIELD.value
    assert normalized_record.normalized_data is None


def test_csv_upload_saved_record_normalizes_into_shared_shape() -> None:
    """CSV-upload raw records should normalize into a rows list."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-csv-1",
        source_id="source-csv-1",
        provider=ProviderKind.CSV_UPLOAD,
        source_type=SourceKind.CSV,
        query=[
            {"name": "Maya Patel", "email": "maya@example.com"},
            {"name": "Omar Ruiz", "email": "omar@example.com"},
        ],
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[
            {"name": "Maya Patel", "email": "maya@example.com"},
            {"name": "Omar Ruiz", "email": "omar@example.com"},
        ],
        metadata={"row_count": 2},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert len(normalized_record.normalized_data["rows"]) == 2
    assert normalized_record.normalized_data["rows"][0]["email"] == "maya@example.com"


def test_csv_upload_empty_rows_normalize_cleanly() -> None:
    """CSV-upload normalization should allow an empty row list."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-csv-2",
        source_id="source-csv-2",
        provider=ProviderKind.CSV_UPLOAD,
        source_type=SourceKind.CSV,
        query=[],
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[],
        metadata={"row_count": 0},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data == {"rows": []}


def test_csv_upload_normalization_returns_error_for_bad_row_type() -> None:
    """CSV-upload normalization should fail when one row is not a dictionary."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-csv-3",
        source_id="source-csv-3",
        provider=ProviderKind.CSV_UPLOAD,
        source_type=SourceKind.CSV,
        query=[{"name": "Maya Patel"}, "bad-row"],
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[{"name": "Maya Patel"}, "bad-row"],
        metadata={"row_count": 2},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


def test_manual_input_saved_record_normalizes_into_shared_shape() -> None:
    """Manual-input raw records should normalize into a fields object."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-man-1",
        source_id="source-man-1",
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        query={
            "note": "Possible link between Maya Patel and portal.example.com",
            "person_name": "Maya Patel",
            "domain": "portal.example.com",
        },
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={
            "note": "Possible link between Maya Patel and portal.example.com",
            "person_name": "Maya Patel",
            "domain": "portal.example.com",
        },
        metadata={"entered_by": "analyst"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["fields"]["note"].startswith("Possible link")


def test_manual_input_normalization_returns_error_for_wrong_top_level_shape() -> None:
    """Manual-input normalization should fail when raw data is not a dictionary."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-man-2",
        source_id="source-man-2",
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        query={"note": "Possible link"},
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=["bad-top-level"],
        metadata={"entered_by": "analyst"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_BAD_RAW_DATA.value
    assert normalized_record.normalized_data is None


def test_manual_input_error_saved_record_passes_through_as_normalized_error() -> None:
    """Failed manual-input raw records should stay failed after normalization."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-man-3",
        source_id="source-man-3",
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        query={"person_name": "Maya Patel"},
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.ERROR,
        raw_data=None,
        error=ProviderError(
            code=ErrorCode.MISSING_REQUIRED_FIELD.value,
            message="Manual input requires a note field.",
        ),
        metadata={"entered_by": "analyst"},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.MISSING_REQUIRED_FIELD.value
    assert normalized_record.normalized_data is None


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


def test_normalization_router_supports_crt_sh() -> None:
    """Providers with a normalizer should route to the expected normalizer."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-5",
        source_id="source-5",
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        query="example.com",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data=[{"common_name": "example.com"}],
        metadata={},
    )

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.SUCCESS
    assert normalized_record.normalized_data["certificates"][0]["common_name"] == "example.com"


def test_normalization_router_returns_clean_error_for_still_unsupported_provider() -> None:
    """Providers without a normalizer should return a clean normalization error."""
    saved_raw_record = SavedRawRecord(
        record_id="raw-6",
        source_id="source-6",
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        query="8.8.8.8",
        fetched_at="2026-04-26T00:00:00+00:00",
        saved_at="2026-04-26T00:00:01+00:00",
        status=FetchStatus.SUCCESS,
        raw_data={"ip": "8.8.8.8"},
        metadata={},
    )
    saved_raw_record.provider = "unknown-provider"

    normalized_record = normalize_saved_raw_record(saved_raw_record)

    assert normalized_record.status == FetchStatus.ERROR
    assert normalized_record.error is not None
    assert normalized_record.error.code == ErrorCode.NORMALIZATION_UNSUPPORTED_PROVIDER.value
