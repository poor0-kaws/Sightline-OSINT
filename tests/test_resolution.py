"""Tests for rule-based person record resolution."""

from __future__ import annotations

from backend.normalization.schemas import NormalizedRecord
from backend.resolution import EntityType
from backend.resolution import MatchCandidate
from backend.resolution import PersonRecord
from backend.resolution import ResolutionDecision
from backend.resolution import build_match_candidates_from_normalized_record
from backend.resolution import resolve_match_candidate_batch
from backend.resolution import resolve_normalized_records
from backend.resolution import resolve_match_candidates
from backend.resolution import resolve_person_records
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind


def test_resolution_merges_when_strong_signals_and_bonus_push_confidence_to_ninety() -> None:
    """Strong matching signals should reach the strict merge threshold."""
    left_record = PersonRecord(
        record_id="person-1",
        full_name="Maya Patel",
        emails=["maya.patel@gmail.com"],
        phone_numbers=["+1 (317) 555-0101"],
        company_name="OpenAI LLC",
        city="Indianapolis",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-2",
        full_name="Maya Patel",
        emails=["maya.patel@gmail.com"],
        phone_numbers=["3175550101"],
        company_name="OpenAI",
        city="Indianapolis",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 100
    assert result.decision == ResolutionDecision.MERGE
    assert [reason.helper_name for reason in result.reasons] == [
        "email_match",
        "phone_match",
        "name_match",
        "company_match",
        "location_match",
        "cross_signal_bonus",
    ]


def test_resolution_puts_same_phone_name_company_record_into_review_band() -> None:
    """Strong but incomplete evidence should stay review-needed, not auto-merge."""
    left_record = PersonRecord(
        record_id="person-3",
        full_name="Maya Patel",
        emails=["maya.work@example.org"],
        phone_numbers=["317-555-0101"],
        company_name="OpenAI LLC",
        city="Austin",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-4",
        full_name="Maya Patel",
        emails=["maya.personal@example.net"],
        phone_numbers=["+1 317 555 0101"],
        company_name="OpenAI",
        city="Seattle",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 75
    assert result.decision == ResolutionDecision.REVIEW_NEEDED


def test_resolution_role_email_does_not_earn_email_confidence() -> None:
    """Shared role mailboxes should not count as personal exact matches."""
    left_record = PersonRecord(
        record_id="person-5",
        full_name="Chris Lane",
        emails=["support@company.com"],
        phone_numbers=["3175550101"],
        company_name="Company LLC",
        city="Indianapolis",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-6",
        full_name="Chris Lane",
        emails=["support@company.com"],
        phone_numbers=["3175550101"],
        company_name="Company",
        city="Indianapolis",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 85
    assert result.decision == ResolutionDecision.REVIEW_NEEDED
    assert all(reason.helper_name != "email_match" for reason in result.reasons)


def test_resolution_shared_family_phone_stays_below_review_without_supporting_signals() -> None:
    """One shared phone alone should not be enough to push a merge or review."""
    left_record = PersonRecord(
        record_id="person-7",
        full_name="Alice Carter",
        phone_numbers=["3175550101"],
        company_name="Northwind LLC",
        city="Chicago",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-8",
        full_name="Bob Carter",
        phone_numbers=["317-555-0101"],
        company_name="Southwind LLC",
        city="Boston",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 20
    assert result.decision == ResolutionDecision.NO_MATCH


def test_resolution_same_name_company_location_without_identifier_hits_review_floor() -> None:
    """Supporting signals alone can reach the review band but not auto-merge."""
    left_record = PersonRecord(
        record_id="person-9",
        full_name="Jordan Lee",
        company_name="Acme Incorporated",
        city="Denver",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-10",
        full_name="Jordan Lee",
        company_name="Acme Inc.",
        city="Denver",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 45
    assert result.decision == ResolutionDecision.NO_MATCH


def test_resolution_exact_email_name_and_location_earns_cross_signal_bonus() -> None:
    """One strong identifier plus two strong supporting signals can auto-merge."""
    left_record = PersonRecord(
        record_id="person-11",
        full_name="Rina Shah",
        emails=["rina.shah@personalmail.com"],
        city="Phoenix",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-12",
        full_name="Rina Shah",
        emails=["rina.shah@personalmail.com"],
        city="Phoenix",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 65
    assert result.decision == ResolutionDecision.REVIEW_NEEDED
    assert [reason.helper_name for reason in result.reasons] == [
        "email_match",
        "name_match",
        "location_match",
        "cross_signal_bonus",
    ]


def test_resolution_placeholder_phone_and_email_do_not_raise_confidence() -> None:
    """Obvious placeholder values should not count toward confidence."""
    left_record = PersonRecord(
        record_id="person-13",
        full_name="Taylor Young",
        emails=["test@example.com"],
        phone_numbers=["123-456-7890"],
    )
    right_record = PersonRecord(
        record_id="person-14",
        full_name="Taylor Young",
        emails=["test@example.com"],
        phone_numbers=["1234567890"],
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 20
    assert result.decision == ResolutionDecision.NO_MATCH
    assert [reason.helper_name for reason in result.reasons] == ["name_match"]


def test_resolution_same_email_does_not_merge_related_companies() -> None:
    """Matching person records should not require company names to merge too."""
    left_record = PersonRecord(
        record_id="person-15",
        full_name="Robin Kim",
        emails=["robin.kim@personalmail.com"],
        phone_numbers=["3175550101"],
        company_name="Google LLC",
        city="Mountain View",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-16",
        full_name="Robin Kim",
        emails=["robin.kim@personalmail.com"],
        phone_numbers=["3175550101"],
        company_name="YouTube LLC",
        city="Mountain View",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 85
    assert result.decision == ResolutionDecision.REVIEW_NEEDED


def test_resolution_missing_email_and_phone_can_still_review_when_other_signals_stack() -> None:
    """Missing strong identifiers should still allow review-needed outcomes."""
    left_record = PersonRecord(
        record_id="person-17",
        full_name="Sam Ortiz",
        company_name="Brightline LLC",
        city="Miami",
        country="US",
    )
    right_record = PersonRecord(
        record_id="person-18",
        full_name="Sam Ortiz",
        company_name="Brightline",
        city="Miami",
        country="US",
    )

    result = resolve_person_records(left_record, right_record)

    assert result.confidence_percent == 45
    assert result.decision == ResolutionDecision.NO_MATCH


def test_general_resolution_merges_exact_domain_candidates_case_insensitively() -> None:
    """Same domains should merge even when letter case is different."""
    left_candidate = MatchCandidate(
        record_id="domain-1",
        entity_type=EntityType.DOMAIN,
        canonical_value="Example.COM",
        display_value="Example.COM",
    )
    right_candidate = MatchCandidate(
        record_id="domain-2",
        entity_type=EntityType.DOMAIN,
        canonical_value="example.com",
        display_value="example.com",
    )

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 100
    assert result.decision == ResolutionDecision.MERGE
    assert [reason.helper_name for reason in result.reasons] == ["domain_exact_match"]


def test_general_resolution_returns_no_match_for_different_domains() -> None:
    """Different domains should never merge on the exact-match path."""
    left_candidate = MatchCandidate(record_id="domain-3", entity_type=EntityType.DOMAIN, canonical_value="example.com")
    right_candidate = MatchCandidate(record_id="domain-4", entity_type=EntityType.DOMAIN, canonical_value="example.org")

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 0
    assert result.decision == ResolutionDecision.NO_MATCH


def test_general_resolution_returns_no_match_for_blank_domain_values() -> None:
    """Blank domain candidates should fail safely instead of crashing."""
    left_candidate = MatchCandidate(record_id="domain-5", entity_type=EntityType.DOMAIN, canonical_value=" ")
    right_candidate = MatchCandidate(record_id="domain-6", entity_type=EntityType.DOMAIN, canonical_value="example.com")

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 0
    assert result.decision == ResolutionDecision.NO_MATCH


def test_general_resolution_merges_exact_ip_candidates() -> None:
    """Same IP addresses should merge immediately on exact match."""
    left_candidate = MatchCandidate(record_id="ip-1", entity_type=EntityType.IP, canonical_value="8.8.8.8")
    right_candidate = MatchCandidate(record_id="ip-2", entity_type=EntityType.IP, canonical_value="8.8.8.8")

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 100
    assert result.decision == ResolutionDecision.MERGE
    assert [reason.helper_name for reason in result.reasons] == ["ip_exact_match"]


def test_general_resolution_returns_no_match_for_different_ips() -> None:
    """Different IP addresses should stay separate."""
    left_candidate = MatchCandidate(record_id="ip-3", entity_type=EntityType.IP, canonical_value="8.8.8.8")
    right_candidate = MatchCandidate(record_id="ip-4", entity_type=EntityType.IP, canonical_value="1.1.1.1")

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 0
    assert result.decision == ResolutionDecision.NO_MATCH


def test_general_resolution_returns_no_match_for_blank_ip_values() -> None:
    """Blank IP candidates should return a clean no-match result."""
    left_candidate = MatchCandidate(record_id="ip-5", entity_type=EntityType.IP, canonical_value="")
    right_candidate = MatchCandidate(record_id="ip-6", entity_type=EntityType.IP, canonical_value="8.8.8.8")

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 0
    assert result.decision == ResolutionDecision.NO_MATCH


def test_general_resolution_returns_no_match_for_mixed_entity_types() -> None:
    """A domain and an IP should never be compared as the same entity."""
    left_candidate = MatchCandidate(record_id="mixed-1", entity_type=EntityType.DOMAIN, canonical_value="example.com")
    right_candidate = MatchCandidate(record_id="mixed-2", entity_type=EntityType.IP, canonical_value="8.8.8.8")

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 0
    assert result.decision == ResolutionDecision.NO_MATCH


def test_general_resolution_delegates_person_candidates_to_existing_person_engine() -> None:
    """Person candidates should reuse the already-tested person scoring path."""
    left_candidate = MatchCandidate(
        record_id="person-candidate-1",
        entity_type=EntityType.PERSON,
        attributes={
            "full_name": "Maya Patel",
            "emails": ["maya.patel@gmail.com"],
            "phone_numbers": ["3175550101"],
            "company_name": "OpenAI LLC",
            "city": "Indianapolis",
            "country": "US",
        },
    )
    right_candidate = MatchCandidate(
        record_id="person-candidate-2",
        entity_type=EntityType.PERSON,
        attributes={
            "full_name": "Maya Patel",
            "emails": ["maya.patel@gmail.com"],
            "phone_numbers": ["+1 (317) 555-0101"],
            "company_name": "OpenAI",
            "city": "Indianapolis",
            "country": "US",
        },
    )

    result = resolve_match_candidates(left_candidate, right_candidate)

    assert result.confidence_percent == 100
    assert result.decision == ResolutionDecision.MERGE


def test_candidate_builder_extracts_ip_candidate_from_ipinfo_record() -> None:
    """IPinfo normalized output should produce one exact-match-ready IP candidate."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="raw-ip-1",
        query="8.8.8.8",
        status=FetchStatus.SUCCESS,
        normalized_data={"ip_address": "8.8.8.8"},
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert len(candidates) == 1
    assert candidates[0].entity_type == EntityType.IP
    assert candidates[0].canonical_value == "8.8.8.8"


def test_candidate_builder_extracts_unique_domains_from_crt_sh_record() -> None:
    """crt.sh normalized certificates should become deduplicated domain candidates."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.API,
        raw_record_id="raw-crt-1",
        query="example.com",
        status=FetchStatus.SUCCESS,
        normalized_data={
            "certificates": [
                {
                    "common_name": "Example.com",
                    "name_value": "example.com\nwww.example.com\n8.8.8.8",
                }
            ]
        },
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert [candidate.canonical_value for candidate in candidates] == [
        "example.com",
        "www.example.com",
    ]


def test_candidate_builder_returns_empty_for_malformed_crt_sh_certificate_list() -> None:
    """Malformed certificate items should fail safe and produce no candidates."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.API,
        raw_record_id="raw-crt-2",
        query="example.com",
        status=FetchStatus.SUCCESS,
        normalized_data={"certificates": ["bad-item"]},
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert candidates == []


def test_candidate_builder_extracts_person_candidate_from_manual_input_record() -> None:
    """Manual input with person-like fields should become one person candidate."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="raw-manual-1",
        query={"full_name": "Maya Patel"},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "fields": {
                "full_name": "Maya Patel",
                "email": "maya.patel@gmail.com",
                "phone": "3175550101",
                "company": "OpenAI",
                "city": "Indianapolis",
                "country": "US",
            }
        },
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert len(candidates) == 1
    assert candidates[0].entity_type == EntityType.PERSON
    assert candidates[0].attributes["full_name"] == "Maya Patel"
    assert candidates[0].attributes["emails"] == ["maya.patel@gmail.com"]


def test_candidate_builder_returns_empty_when_normalized_record_has_no_usable_fields() -> None:
    """Records without resolvable identifiers should quietly produce no candidates."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="raw-manual-2",
        query={},
        status=FetchStatus.SUCCESS,
        normalized_data={"fields": {"notes": "just a note"}},
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert candidates == []


def test_candidate_builder_returns_empty_for_non_success_normalized_records() -> None:
    """Error and no-results records should not feed the resolution layer."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="raw-ip-2",
        query="8.8.8.8",
        status=FetchStatus.ERROR,
        normalized_data={"ip_address": "8.8.8.8"},
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert candidates == []


def test_candidate_builder_extracts_person_candidate_from_webhook_payload() -> None:
    """Webhook payloads should feed person-like records into resolution."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        raw_record_id="raw-webhook-1",
        query={"event_type": "lead.created"},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "event_type": "lead.created",
            "payload": {
                "full_name": "Maya Patel",
                "email": "maya.patel@gmail.com",
                "phone": "3175550101",
            },
        },
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert len(candidates) == 1
    assert candidates[0].entity_type == EntityType.PERSON
    assert candidates[0].record_id == "raw-webhook-1:payload:person"


def test_candidate_builder_extracts_person_candidates_from_csv_rows() -> None:
    """Each usable CSV row should become a separate person candidate."""
    normalized_record = NormalizedRecord(
        provider=ProviderKind.CSV_UPLOAD,
        source_type=SourceKind.CSV,
        raw_record_id="raw-csv-1",
        query=[],
        status=FetchStatus.SUCCESS,
        normalized_data={
            "rows": [
                {"full_name": "Maya Patel", "email": "maya.patel@gmail.com"},
                {"name": "Omar Ruiz", "email": "omar@example.net"},
                {"notes": "not enough identity data"},
            ]
        },
        metadata={},
    )

    candidates = build_match_candidates_from_normalized_record(normalized_record)

    assert [candidate.record_id for candidate in candidates] == [
        "raw-csv-1:row:0:person",
        "raw-csv-1:row:1:person",
    ]


def test_resolution_batch_merges_candidates_across_normalized_records() -> None:
    """Resolution should compare candidates after normalized records enter the batch service."""
    left_record = NormalizedRecord(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="raw-left",
        query={},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "fields": {
                "full_name": "Maya Patel",
                "email": "maya.patel@gmail.com",
                "phone": "3175550101",
                "company_name": "OpenAI LLC",
                "city": "Indianapolis",
                "country": "US",
            }
        },
        metadata={},
    )
    right_record = NormalizedRecord(
        provider=ProviderKind.WEBHOOK,
        source_type=SourceKind.WEBHOOK,
        raw_record_id="raw-right",
        query={},
        status=FetchStatus.SUCCESS,
        normalized_data={
            "event_type": "lead.created",
            "payload": {
                "full_name": "Maya Patel",
                "email": "maya.patel@gmail.com",
                "phone": "+1 (317) 555-0101",
                "company_name": "OpenAI",
                "city": "Indianapolis",
                "country": "US",
            },
        },
        metadata={},
    )

    result = resolve_normalized_records([left_record, right_record])

    assert result.status == "success"
    assert result.candidate_count == 2
    assert result.comparison_count == 1
    assert result.summary["merge"] == 1
    assert result.matches[0].decision == ResolutionDecision.MERGE


def test_resolution_batch_skips_candidates_from_the_same_raw_record() -> None:
    """Candidates from the same saved raw record should not resolve against themselves."""
    candidates = [
        MatchCandidate(record_id="raw-1:domain:0", entity_type=EntityType.DOMAIN, canonical_value="example.com"),
        MatchCandidate(record_id="raw-1:domain:1", entity_type=EntityType.DOMAIN, canonical_value="example.com"),
    ]

    result = resolve_match_candidate_batch(candidates, source_record_count=1)

    assert result.candidate_count == 2
    assert result.comparison_count == 0
    assert result.matches == []
