"""Tests for rule-based person record resolution."""

from __future__ import annotations

from backend.resolution import PersonRecord
from backend.resolution import ResolutionDecision
from backend.resolution import resolve_person_records


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
