"""Rule-based entity resolution for person-like records."""

from __future__ import annotations

import re

from backend.resolution.schemas import MatchReason
from backend.resolution.schemas import PersonRecord
from backend.resolution.schemas import ResolutionDecision
from backend.resolution.schemas import ResolutionResult


EMAIL_CONFIDENCE = 15
PHONE_CONFIDENCE = 20
NAME_CONFIDENCE = 20
COMPANY_CONFIDENCE = 15
LOCATION_CONFIDENCE = 10
CROSS_SIGNAL_CONFIDENCE = 20

MERGE_THRESHOLD = 90
REVIEW_THRESHOLD = 60

ROLE_EMAIL_LOCAL_PARTS = {
    "admin",
    "billing",
    "careers",
    "contact",
    "hello",
    "help",
    "hr",
    "info",
    "jobs",
    "privacy",
    "sales",
    "security",
    "support",
    "team",
}
PLACEHOLDER_EMAIL_TOKENS = {"example", "placeholder", "test"}
PHONE_PLACEHOLDER_VALUES = {
    "0000000000",
    "1111111111",
    "1234567890",
    "9999999999",
}
BUSINESS_SUFFIXES = {
    "co",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
}


def resolve_person_records(left_record: PersonRecord, right_record: PersonRecord) -> ResolutionResult:
    """Score whether two person-like records are the same real-world person."""
    reasons: list[MatchReason] = []
    matched_helpers: set[str] = set()

    email_reason = _score_email_match(left_record, right_record)
    if email_reason is not None:
        reasons.append(email_reason)
        matched_helpers.add(email_reason.helper_name)

    phone_reason = _score_phone_match(left_record, right_record)
    if phone_reason is not None:
        reasons.append(phone_reason)
        matched_helpers.add(phone_reason.helper_name)

    name_reason = _score_name_match(left_record, right_record)
    if name_reason is not None:
        reasons.append(name_reason)
        matched_helpers.add(name_reason.helper_name)

    company_reason = _score_company_match(left_record, right_record)
    if company_reason is not None:
        reasons.append(company_reason)
        matched_helpers.add(company_reason.helper_name)

    location_reason = _score_location_match(left_record, right_record)
    if location_reason is not None:
        reasons.append(location_reason)
        matched_helpers.add(location_reason.helper_name)

    cross_signal_reason = _score_cross_signal_bonus(matched_helpers)
    if cross_signal_reason is not None:
        reasons.append(cross_signal_reason)

    confidence_percent = sum(reason.confidence_added for reason in reasons)
    decision = _decide_resolution(confidence_percent)

    return ResolutionResult(
        left_record_id=left_record.record_id,
        right_record_id=right_record.record_id,
        confidence_percent=confidence_percent,
        decision=decision,
        reasons=reasons,
    )


def _score_email_match(left_record: PersonRecord, right_record: PersonRecord) -> MatchReason | None:
    """Award confidence for a rigorously validated exact email match."""
    left_emails = _extract_usable_emails(left_record.emails)
    right_emails = _extract_usable_emails(right_record.emails)
    if not left_emails or not right_emails:
        return None

    matched_emails = sorted(left_emails.intersection(right_emails))
    if not matched_emails:
        return None

    return MatchReason(
        helper_name="email_match",
        confidence_added=EMAIL_CONFIDENCE,
        message=f"Exact personal email match: {matched_emails[0]}",
    )


def _score_phone_match(left_record: PersonRecord, right_record: PersonRecord) -> MatchReason | None:
    """Award confidence for a rigorously validated exact phone match."""
    left_phone_numbers = _extract_usable_phone_numbers(left_record.phone_numbers)
    right_phone_numbers = _extract_usable_phone_numbers(right_record.phone_numbers)
    if not left_phone_numbers or not right_phone_numbers:
        return None

    matched_phone_numbers = sorted(left_phone_numbers.intersection(right_phone_numbers))
    if not matched_phone_numbers:
        return None

    return MatchReason(
        helper_name="phone_match",
        confidence_added=PHONE_CONFIDENCE,
        message=f"Exact normalized phone match: {matched_phone_numbers[0]}",
    )


def _score_name_match(left_record: PersonRecord, right_record: PersonRecord) -> MatchReason | None:
    """Award confidence when both full names normalize to the same value."""
    left_name = _normalize_name(left_record.full_name)
    right_name = _normalize_name(right_record.full_name)
    if not left_name or not right_name:
        return None

    if left_name != right_name:
        return None

    return MatchReason(
        helper_name="name_match",
        confidence_added=NAME_CONFIDENCE,
        message=f"Normalized full names match: {left_name}",
    )


def _score_company_match(left_record: PersonRecord, right_record: PersonRecord) -> MatchReason | None:
    """Award confidence when both company names normalize to the same value."""
    left_company = _normalize_company_name(left_record.company_name)
    right_company = _normalize_company_name(right_record.company_name)
    if not left_company or not right_company:
        return None

    if left_company != right_company:
        return None

    return MatchReason(
        helper_name="company_match",
        confidence_added=COMPANY_CONFIDENCE,
        message=f"Normalized company names match: {left_company}",
    )


def _score_location_match(left_record: PersonRecord, right_record: PersonRecord) -> MatchReason | None:
    """Award confidence when city and country agree after normalization."""
    left_city = _normalize_text(left_record.city)
    right_city = _normalize_text(right_record.city)
    left_country = _normalize_text(left_record.country)
    right_country = _normalize_text(right_record.country)
    if not left_city or not right_city or not left_country or not right_country:
        return None

    if left_city != right_city or left_country != right_country:
        return None

    return MatchReason(
        helper_name="location_match",
        confidence_added=LOCATION_CONFIDENCE,
        message=f"City and country both match: {left_city}, {left_country}",
    )


def _score_cross_signal_bonus(matched_helpers: set[str]) -> MatchReason | None:
    """Award extra confidence when multiple strong signals agree."""
    if {"email_match", "phone_match"}.issubset(matched_helpers):
        return MatchReason(
            helper_name="cross_signal_bonus",
            confidence_added=CROSS_SIGNAL_CONFIDENCE,
            message="Email and phone both matched exactly.",
        )

    if {"phone_match", "name_match", "company_match"}.issubset(matched_helpers):
        return MatchReason(
            helper_name="cross_signal_bonus",
            confidence_added=CROSS_SIGNAL_CONFIDENCE,
            message="Phone, full name, and company all matched.",
        )

    if {"email_match", "name_match", "location_match"}.issubset(matched_helpers):
        return MatchReason(
            helper_name="cross_signal_bonus",
            confidence_added=CROSS_SIGNAL_CONFIDENCE,
            message="Email, full name, and location all matched.",
        )

    return None


def _extract_usable_emails(email_values: list[str]) -> set[str]:
    """Return normalized personal-looking emails that pass the gate checks."""
    usable_emails: set[str] = set()

    for email_value in email_values:
        normalized_email = _normalize_email(email_value)
        if not normalized_email:
            continue

        if _is_role_based_email(normalized_email):
            continue

        if _is_placeholder_email(normalized_email):
            continue

        usable_emails.add(normalized_email)

    return usable_emails


def _extract_usable_phone_numbers(phone_values: list[str]) -> set[str]:
    """Return normalized phone numbers that pass the gate checks."""
    usable_phone_numbers: set[str] = set()

    for phone_value in phone_values:
        normalized_phone = _normalize_phone_number(phone_value)
        if not normalized_phone:
            continue

        if normalized_phone in PHONE_PLACEHOLDER_VALUES:
            continue

        usable_phone_numbers.add(normalized_phone)

    return usable_phone_numbers


def _normalize_email(value: str) -> str:
    """Normalize one email address into a clean comparable string."""
    if not isinstance(value, str):
        return ""

    normalized_value = value.strip().lower()
    if not normalized_value or "@" not in normalized_value:
        return ""

    local_part, separator, domain_part = normalized_value.partition("@")
    if not separator or not local_part or not domain_part:
        return ""

    if "." not in domain_part:
        return ""

    return f"{local_part}@{domain_part}"


def _normalize_phone_number(value: str) -> str:
    """Normalize a phone number into digits only."""
    digits = re.sub(r"\D+", "", _normalize_text(value))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) < 10 or len(digits) > 15:
        return ""

    return digits


def _normalize_name(value: str) -> str:
    """Normalize one person name into a stable comparable string."""
    return _normalize_text(value)


def _normalize_company_name(value: str) -> str:
    """Normalize one company name into a stable comparable string."""
    normalized_value = _normalize_text(value)
    if not normalized_value:
        return ""

    tokens = normalized_value.split()
    while tokens and tokens[-1] in BUSINESS_SUFFIXES:
        tokens.pop()

    return " ".join(tokens).strip()


def _normalize_text(value: str) -> str:
    """Normalize free text by lowercasing and collapsing punctuation/spacing."""
    if not isinstance(value, str):
        return ""

    normalized_value = value.lower().strip()
    if not normalized_value:
        return ""

    normalized_value = re.sub(r"[^a-z0-9]+", " ", normalized_value)
    normalized_value = re.sub(r"\s+", " ", normalized_value)
    return normalized_value.strip()


def _is_role_based_email(email_value: str) -> bool:
    """Return True when the email local part looks like a shared mailbox."""
    local_part = email_value.split("@", 1)[0]
    return local_part in ROLE_EMAIL_LOCAL_PARTS


def _is_placeholder_email(email_value: str) -> bool:
    """Return True when the email looks like test or example data."""
    return any(token in email_value for token in PLACEHOLDER_EMAIL_TOKENS)


def _decide_resolution(confidence_percent: int) -> ResolutionDecision:
    """Turn a confidence score into the final resolution decision."""
    if confidence_percent >= MERGE_THRESHOLD:
        return ResolutionDecision.MERGE

    if confidence_percent >= REVIEW_THRESHOLD:
        return ResolutionDecision.REVIEW_NEEDED

    return ResolutionDecision.NO_MATCH
