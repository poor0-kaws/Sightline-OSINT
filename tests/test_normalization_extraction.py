"""Tests for the second normalization layer that extracts shared artifacts."""

from __future__ import annotations

from backend.normalization.extraction import extract_shared_artifacts
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind


def test_ipinfo_shared_extraction_builds_entities_evidence_and_relationships() -> None:
    """IPinfo normalized output should become graph-ready shared artifacts."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="norm-ip-1",
        query="8.8.8.8",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "ip_address": "8.8.8.8",
            "organization": "AS15169 Google LLC",
            "city": "Mountain View",
            "region": "California",
            "country": "US",
        },
        metadata={"mode": "live"},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert {(entity.entity_type, entity.canonical_value) for entity in enriched_record.entities} == {
        ("ip", "8.8.8.8"),
        ("organization", "as15169 google llc"),
        ("place", "mountain view|california|us"),
    }
    assert len(enriched_record.evidence) == 3
    assert {
        (
            relationship.relationship_type,
            relationship.source_entity_type,
            relationship.target_entity_type,
        )
        for relationship in enriched_record.relationship_candidates
    } == {
        ("associated_with", "ip", "organization"),
        ("located_in", "ip", "place"),
    }


def test_ipinfo_shared_extraction_tolerates_missing_optional_fields() -> None:
    """Missing organization and place should not crash extraction."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="norm-ip-2",
        query="8.8.8.8",
        status=FetchStatus.SUCCESS,
        normalized_data={"ip_address": "8.8.8.8", "organization": "", "city": "", "region": "", "country": ""},
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert len(enriched_record.entities) == 1
    assert enriched_record.entities[0].entity_type == "ip"
    assert enriched_record.relationship_candidates == []


def test_ipinfo_shared_extraction_returns_error_for_bad_normalized_shape() -> None:
    """Malformed provider-normalized data should fail before later layers use it."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="norm-ip-3",
        query="8.8.8.8",
        status=FetchStatus.SUCCESS,
        normalized_data=["bad-shape"],
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert enriched_record.status == FetchStatus.ERROR
    assert enriched_record.error is not None
    assert enriched_record.error.code == ErrorCode.NORMALIZATION_BAD_NORMALIZED_DATA.value
    assert enriched_record.normalized_data is None
    assert enriched_record.entities == []


def test_crt_sh_shared_extraction_dedupes_domains_and_handles_wildcards() -> None:
    """crt.sh wildcard and duplicate domain values should normalize safely."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.API,
        raw_record_id="norm-crt-1",
        query="example.com",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "certificates": [
                {
                    "common_name": "Example.com",
                    "issuer_name": "Let's Encrypt",
                    "name_value": "*.example.com\nexample.com\nwww.example.com\n8.8.8.8",
                }
            ]
        },
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert {(entity.entity_type, entity.canonical_value) for entity in enriched_record.entities} == {
        ("domain", "example.com"),
        ("domain", "www.example.com"),
        ("organization", "let s encrypt"),
    }
    assert {
        relationship.target_canonical_value
        for relationship in enriched_record.relationship_candidates
        if relationship.relationship_type == "certified_by"
    } == {"let s encrypt"}


def test_crt_sh_shared_extraction_returns_error_for_bad_certificate_item() -> None:
    """Broken certificate items should stop deeper normalization cleanly."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.API,
        raw_record_id="norm-crt-2",
        query="example.com",
        status=FetchStatus.SUCCESS,
        normalized_data={"certificates": ["bad-item"]},
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert enriched_record.status == FetchStatus.ERROR
    assert enriched_record.error is not None
    assert enriched_record.error.code == ErrorCode.NORMALIZATION_BAD_NORMALIZED_DATA.value


def test_nominatim_shared_extraction_builds_place_entities_for_search_results() -> None:
    """Nominatim search places should become shared place entities and evidence."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        raw_record_id="norm-nom-1",
        query="Indianapolis",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "places": [
                {
                    "display_name": "Indianapolis, Marion County, Indiana, United States",
                    "latitude": 39.7684,
                    "longitude": -86.1581,
                }
            ]
        },
        metadata={"mode": "search"},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert len(enriched_record.entities) == 1
    assert enriched_record.entities[0].entity_type == "place"
    assert enriched_record.entities[0].metadata["latitude"] == 39.7684
    assert len(enriched_record.evidence) == 1


def test_nominatim_shared_extraction_returns_error_for_bad_places_shape() -> None:
    """Broken place lists should be caught in the second normalization layer too."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        raw_record_id="norm-nom-2",
        query="Indianapolis",
        status=FetchStatus.SUCCESS,
        normalized_data={"places": ["bad-place"]},
        metadata={"mode": "search"},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert enriched_record.status == FetchStatus.ERROR
    assert enriched_record.error is not None
    assert enriched_record.error.code == ErrorCode.NORMALIZATION_BAD_NORMALIZED_DATA.value


def test_webhook_shared_extraction_builds_generic_entities_and_relationships() -> None:
    """Webhook payloads should produce shared entities and simple relationship candidates."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        raw_record_id="norm-web-1",
        query={},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "event_type": "breach.alert",
            "payload": {
                "person_name": "Maya Patel",
                "email": "maya@example.com",
                "domain": "portal.example.com",
                "ip_address": "8.8.8.8",
                "organization": "OpenAI",
            },
        },
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert {(entity.entity_type, entity.canonical_value) for entity in enriched_record.entities} == {
        ("person", "maya patel"),
        ("email", "maya@example.com"),
        ("domain", "portal.example.com"),
        ("ip", "8.8.8.8"),
        ("organization", "openai"),
    }
    assert {
        (
            relationship.relationship_type,
            relationship.source_entity_type,
            relationship.target_entity_type,
        )
        for relationship in enriched_record.relationship_candidates
    } == {
        ("uses", "person", "email"),
        ("associated_with", "person", "domain"),
        ("associated_with", "person", "organization"),
        ("points_to", "domain", "ip"),
        ("associated_with", "ip", "organization"),
    }


def test_csv_shared_extraction_ignores_bad_optional_field_types_without_crashing() -> None:
    """Bad optional field values inside valid rows should be skipped, not explode extraction."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.CSV_UPLOAD,
        source_type=SourceKind.CSV,
        raw_record_id="norm-csv-1",
        query=[],
        status=FetchStatus.SUCCESS,
        normalized_data={
            "rows": [
                {
                    "name": "Maya Patel",
                    "email": "maya@example.com",
                    "domain": 123,
                    "ip_address": None,
                    "company": "OpenAI",
                }
            ]
        },
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert {(entity.entity_type, entity.canonical_value) for entity in enriched_record.entities} == {
        ("person", "maya patel"),
        ("email", "maya@example.com"),
        ("company", "openai"),
    }


def test_manual_input_shared_extraction_allows_note_only_records() -> None:
    """Notes without resolvable entities should stay successful and just produce empty lists."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="norm-man-1",
        query={},
        status=FetchStatus.SUCCESS,
        normalized_data={"fields": {"note": "Need to investigate later."}},
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert enriched_record.status == FetchStatus.SUCCESS
    assert enriched_record.entities == []
    assert enriched_record.evidence == []
    assert enriched_record.relationship_candidates == []


def test_opensky_shared_extraction_builds_aircraft_and_place_relationship() -> None:
    """OpenSky aircraft data should become aircraft plus observation place artifacts."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        raw_record_id="norm-open-1",
        query="AAL123",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "aircraft": {
                "icao24": "abc123",
                "callsign": "AAL123",
                "origin_country": "United States",
                "longitude": -86.1581,
                "latitude": 39.7684,
                "baro_altitude": 11200.0,
            }
        },
        metadata={"mode": "aircraft"},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert {(entity.entity_type, entity.canonical_value) for entity in enriched_record.entities} == {
        ("aircraft", "abc123"),
        ("place", "39.7684,-86.1581"),
    }
    assert len(enriched_record.relationship_candidates) == 1
    assert enriched_record.relationship_candidates[0].relationship_type == "observed_over"


def test_no_results_records_keep_empty_shared_artifacts() -> None:
    """No-results records should not be turned into errors by the second layer."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.API,
        raw_record_id="norm-none-1",
        query="example.com",
        status=FetchStatus.NO_RESULTS,
        normalized_data={"certificates": []},
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert enriched_record.status == FetchStatus.NO_RESULTS
    assert enriched_record.entities == []
    assert enriched_record.evidence == []
    assert enriched_record.relationship_candidates == []


def test_error_records_pass_through_without_new_shared_artifacts() -> None:
    """Already-failed records should not try to extract entities."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="norm-error-1",
        query="8.8.8.8",
        status=FetchStatus.ERROR,
        error=ProviderError(
            code=ErrorCode.PROVIDER_TIMEOUT.value,
            message="Timed out.",
        ),
        normalized_data=None,
        metadata={},
    )

    enriched_record = extract_shared_artifacts(normalized_record)

    assert enriched_record.status == FetchStatus.ERROR
    assert enriched_record.error is not None
    assert enriched_record.error.code == ErrorCode.PROVIDER_TIMEOUT.value
    assert enriched_record.entities == []
