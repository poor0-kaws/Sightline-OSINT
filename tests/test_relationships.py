"""Tests for strict relationship extraction from normalized records."""

from __future__ import annotations

from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind


def test_crt_sh_extractor_dedupes_domains_strips_wildcards_and_ignores_bad_values() -> None:
    """One certificate should only create clean unique domain edges."""
    from backend.relationships import EntityType
    from backend.relationships import RelationshipType
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        raw_record_id="raw-crt-1",
        query="example.com",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "certificates": [
                {
                    "common_name": "Example.com",
                    "issuer_name": "Let's Encrypt",
                    "not_before": "2026-01-01",
                    "name_value": "*.example.com\nexample.com\napi.example.com\napi.example.com\nnot a domain",
                }
            ]
        },
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.SUCCESS
    assert len(result.relationships) == 3

    domain_relationships = [
        relationship
        for relationship in result.relationships
        if relationship.relationship_type == RelationshipType.CERTIFICATE_MENTIONS_DOMAIN
    ]
    issuer_relationships = [
        relationship
        for relationship in result.relationships
        if relationship.relationship_type == RelationshipType.CERTIFICATE_ISSUED_BY
    ]

    assert len(domain_relationships) == 2
    assert len(issuer_relationships) == 1
    assert {relationship.to_entity.canonical_value for relationship in domain_relationships} == {
        "example.com",
        "api.example.com",
    }
    assert all(relationship.from_entity.entity_type == EntityType.CERTIFICATE for relationship in domain_relationships)
    assert issuer_relationships[0].to_entity.entity_type == EntityType.ISSUER
    assert issuer_relationships[0].to_entity.display_value == "Let's Encrypt"


def test_crt_sh_extractor_returns_error_when_certificate_item_is_not_a_dictionary() -> None:
    """Malformed certificate bundles should fail loudly instead of guessing."""
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        raw_record_id="raw-crt-2",
        query="example.com",
        status=FetchStatus.SUCCESS,
        normalized_data={"certificates": ["bad-certificate-row"]},
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.ERROR
    assert result.relationships == []
    assert result.error is not None
    assert result.error.code == "relationship_bad_normalized_data"


def test_manual_input_extractor_keeps_only_valid_unique_person_contact_edges() -> None:
    """Duplicate, role-based, and placeholder contact values should be filtered out."""
    from backend.relationships import RelationshipType
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="raw-manual-1",
        query={"case_id": "case-1"},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "fields": {
                "full_name": "Alice Ng",
                "emails": [
                    "alice@personalmail.org",
                    "ALICE@personalmail.org",
                    "support@personalmail.org",
                    "test@example.com",
                    "not-an-email",
                ],
                "phone_numbers": [
                    "+1 (317) 555-0101",
                    "3175550101",
                    "123-456-7890",
                    "abc",
                ],
                "company_name": "OpenAI LLC",
            }
        },
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.SUCCESS
    assert [relationship.relationship_type for relationship in result.relationships] == [
        RelationshipType.PERSON_USES_EMAIL,
        RelationshipType.PERSON_USES_PHONE,
        RelationshipType.PERSON_ASSOCIATED_WITH_COMPANY,
    ]
    assert result.relationships[0].to_entity.canonical_value == "alice@personalmail.org"
    assert result.relationships[1].to_entity.canonical_value == "3175550101"
    assert result.relationships[2].to_entity.display_value == "OpenAI LLC"


def test_webhook_extractor_returns_no_results_when_payload_is_not_person_like() -> None:
    """A clean payload with no clear entity pairs should produce no edges."""
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        raw_record_id="raw-webhook-1",
        query={"event_id": "evt-1"},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "event_type": "status.update",
            "payload": {"severity": "high", "message": "pipeline completed"},
        },
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.NO_RESULTS
    assert result.relationships == []
    assert result.error is None


def test_ipinfo_extractor_builds_org_and_location_edges_when_fields_are_complete() -> None:
    """Clear IP intelligence should turn into graph-ready edges."""
    from backend.relationships import RelationshipType
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="raw-ipinfo-1",
        query="8.8.8.8",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "ip_address": "8.8.8.8",
            "organization": "AS15169 Google LLC",
            "city": "Mountain View",
            "region": "California",
            "country": "US",
        },
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.SUCCESS
    assert [relationship.relationship_type for relationship in result.relationships] == [
        RelationshipType.IP_BELONGS_TO_ORGANIZATION,
        RelationshipType.IP_LOCATED_IN,
    ]
    assert result.relationships[0].to_entity.display_value == "AS15169 Google LLC"
    assert result.relationships[1].to_entity.display_value == "Mountain View, California, US"


def test_ipinfo_extractor_returns_no_results_for_partial_location_and_blank_org() -> None:
    """Weak IPinfo fragments should not create low-quality graph edges."""
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="raw-ipinfo-2",
        query="8.8.4.4",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "ip_address": "8.8.4.4",
            "organization": "   ",
            "city": "Mountain View",
            "region": "",
            "country": "",
        },
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.NO_RESULTS
    assert result.relationships == []


def test_non_success_normalized_record_passes_through_without_extraction() -> None:
    """Upstream failures should flow through instead of creating fake edges."""
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="raw-error-1",
        query="8.8.8.8",
        status=FetchStatus.ERROR,
        error=ProviderError(code="provider_timeout", message="The provider timed out."),
        normalized_data=None,
        metadata={"phase": "normalization"},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.ERROR
    assert result.relationships == []
    assert result.error is not None
    assert result.error.code == "provider_timeout"


def test_unsupported_provider_returns_a_clean_error_result() -> None:
    """Unknown providers should fail cleanly instead of crashing the router."""
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord.model_construct(
        provider="unknown-provider",
        source_type=SourceKind.API,
        raw_record_id="raw-unknown-1",
        query="mystery",
        status=FetchStatus.SUCCESS,
        normalized_data={},
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.ERROR
    assert result.relationships == []
    assert result.error is not None
    assert result.error.code == "relationship_unsupported_provider"


def test_nominatim_record_returns_no_relationships_in_v1() -> None:
    """A standalone place record should stay edge-free until graph rules expand."""
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        raw_record_id="raw-nominatim-1",
        query={"lat": 39.7684, "lon": -86.1581},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "place": {
                "display_name": "Indianapolis, Indiana, United States",
                "latitude": 39.7684,
                "longitude": -86.1581,
            }
        },
        metadata={"mode": "reverse"},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.NO_RESULTS
    assert result.relationships == []


def test_opensky_record_extracts_aircraft_observed_over_place_relationship() -> None:
    """OpenSky aircraft coordinates should become an aircraft-place graph edge."""
    from backend.normalization.schemas import NormalizedRelationshipCandidate
    from backend.relationships import EntityType
    from backend.relationships import RelationshipType
    from backend.relationships import extract_relationships_from_normalized_record

    normalized_record = NormalizedRecord(
        provider=ProviderKind.OPENSKY,
        source_type=SourceKind.API,
        raw_record_id="raw-opensky-1",
        query="AAL123",
        status=FetchStatus.SUCCESS,
        normalized_data={"aircraft": {"icao24": "abc123"}},
        relationship_candidates=[
            NormalizedRelationshipCandidate(
                relationship_type="observed_over",
                source_entity_type="aircraft",
                source_canonical_value="abc123",
                target_entity_type="place",
                target_canonical_value="39.7684|-86.1581",
            )
        ],
        metadata={},
    )

    result = extract_relationships_from_normalized_record(normalized_record)

    assert result.status == FetchStatus.SUCCESS
    assert result.relationships[0].relationship_type == RelationshipType.AIRCRAFT_OBSERVED_OVER
    assert result.relationships[0].from_entity.entity_type == EntityType.AIRCRAFT
