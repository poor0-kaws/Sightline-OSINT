"""Shared helpers for strict relationship extraction."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.relationships.schemas import EntityReference
from backend.relationships.schemas import EntityType
from backend.relationships.schemas import ExtractedRelationship
from backend.relationships.schemas import RelationshipExtractionResult
from backend.relationships.schemas import RelationshipType
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.utils.text import slugify
from backend.utils.text import to_text
from backend.utils.validation import is_valid_domain_name


ROLE_EMAIL_PREFIXES = {
    "admin",
    "billing",
    "contact",
    "hello",
    "help",
    "info",
    "sales",
    "support",
}
PLACEHOLDER_EMAIL_LOCAL_PARTS = {"placeholder", "test"}
PLACEHOLDER_EMAIL_DOMAINS = {"example.com"}
PHONE_PLACEHOLDER_VALUES = {"0000000000", "1111111111", "1234567890"}
BUSINESS_SUFFIXES = {"co", "corp", "corporation", "inc", "incorporated", "llc", "ltd", "limited"}


def build_passthrough_result(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Return the upstream status unchanged when extraction should not run."""
    return RelationshipExtractionResult(
        provider=_get_safe_provider(normalized_record),
        source_type=normalized_record.source_type,
        raw_record_id=normalized_record.raw_record_id,
        query=normalized_record.query,
        status=normalized_record.status,
        error=normalized_record.error,
        relationships=[],
        metadata=dict(normalized_record.metadata),
    )


def build_error_result(
    normalized_record: NormalizedRecord,
    *,
    code: ErrorCode,
    message: str,
) -> RelationshipExtractionResult:
    """Build one strict error result."""
    metadata = dict(normalized_record.metadata)
    requested_provider = _get_provider_text(normalized_record)
    if requested_provider:
        metadata["requested_provider"] = requested_provider

    return RelationshipExtractionResult(
        provider=_get_safe_provider(normalized_record),
        source_type=normalized_record.source_type,
        raw_record_id=normalized_record.raw_record_id,
        query=normalized_record.query,
        status=FetchStatus.ERROR,
        error=ProviderError(code=code.value, message=message),
        relationships=[],
        metadata=metadata,
    )


def build_no_results_result(
    normalized_record: NormalizedRecord,
    *,
    metadata_updates: dict[str, Any] | None = None,
) -> RelationshipExtractionResult:
    """Build a clean no-results response when no trustworthy edges exist."""
    metadata = dict(normalized_record.metadata)
    if metadata_updates:
        metadata.update(metadata_updates)

    return RelationshipExtractionResult(
        provider=_get_safe_provider(normalized_record),
        source_type=normalized_record.source_type,
        raw_record_id=normalized_record.raw_record_id,
        query=normalized_record.query,
        status=FetchStatus.NO_RESULTS,
        error=None,
        relationships=[],
        metadata=metadata,
    )


def build_success_result(
    normalized_record: NormalizedRecord,
    *,
    relationships: list[ExtractedRelationship],
    metadata_updates: dict[str, Any] | None = None,
) -> RelationshipExtractionResult:
    """Build a success response for one normalized record."""
    metadata = dict(normalized_record.metadata)
    metadata["relationship_count"] = len(relationships)
    if metadata_updates:
        metadata.update(metadata_updates)

    return RelationshipExtractionResult(
        provider=_get_safe_provider(normalized_record),
        source_type=normalized_record.source_type,
        raw_record_id=normalized_record.raw_record_id,
        query=normalized_record.query,
        status=FetchStatus.SUCCESS,
        error=None,
        relationships=relationships,
        metadata=metadata,
    )


def build_entity_reference(
    *,
    record_scope: str,
    entity_type: EntityType,
    canonical_value: str,
    display_value: str,
) -> EntityReference:
    """Create one easy-to-read entity reference."""
    entity_id = f"{record_scope}:{entity_type.value}:{slugify(canonical_value or display_value)}"
    return EntityReference(
        entity_id=entity_id,
        entity_type=entity_type,
        canonical_value=canonical_value,
        display_value=display_value,
    )


def build_relationship(
    *,
    relationship_id: str,
    relationship_type: RelationshipType,
    from_entity: EntityReference,
    to_entity: EntityReference,
    confidence_percent: int,
    evidence_record_id: str,
    metadata: dict[str, Any] | None = None,
) -> ExtractedRelationship:
    """Create one graph-ready relationship record."""
    return ExtractedRelationship(
        relationship_id=relationship_id,
        relationship_type=relationship_type,
        from_entity=from_entity,
        to_entity=to_entity,
        confidence_percent=confidence_percent,
        evidence_record_id=evidence_record_id,
        metadata=metadata or {},
    )


def normalize_email(value: Any) -> str:
    """Return one clean email when it passes the strict domain check."""
    if not isinstance(value, str):
        return ""

    candidate = value.strip().lower()
    if not candidate:
        return ""

    if candidate.count("@") != 1:
        return ""

    local_part, domain_part = candidate.split("@", 1)
    if not local_part or not domain_part:
        return ""

    if not is_valid_domain_name(domain_part):
        return ""

    return candidate


def is_role_based_email(email_value: str) -> bool:
    """Return True when the email local-part looks shared instead of personal."""
    if "@" not in email_value:
        return False

    local_part = email_value.split("@", 1)[0]
    return local_part in ROLE_EMAIL_PREFIXES


def is_placeholder_email(email_value: str) -> bool:
    """Return True when the email looks like obvious test data."""
    if "@" not in email_value:
        return False

    local_part, domain_part = email_value.split("@", 1)
    if local_part in PLACEHOLDER_EMAIL_LOCAL_PARTS:
        return True

    return domain_part in PLACEHOLDER_EMAIL_DOMAINS


def normalize_phone_number(value: Any) -> str:
    """Return a normalized 10-digit phone number, or an empty string."""
    if not isinstance(value, str):
        return ""

    digits_only = "".join(character for character in value if character.isdigit())
    if not digits_only:
        return ""

    if len(digits_only) == 11 and digits_only.startswith("1"):
        digits_only = digits_only[1:]

    if len(digits_only) != 10:
        return ""

    return digits_only


def is_placeholder_phone_number(phone_value: str) -> bool:
    """Return True when the phone number is obvious filler."""
    return phone_value in PHONE_PLACEHOLDER_VALUES


def normalize_company_canonical(value: Any) -> str:
    """Return a simple company key for graph nodes."""
    cleaned_value = to_text(value).lower()
    if not cleaned_value:
        return ""

    tokens: list[str] = []
    for token in cleaned_value.replace(",", " ").replace(".", " ").split():
        if token in BUSINESS_SUFFIXES:
            continue
        tokens.append(token)

    if not tokens:
        return ""

    return " ".join(tokens)


def normalize_location_values(city_value: Any, region_value: Any, country_value: Any) -> tuple[str, str]:
    """Return one clean location display + canonical key when the location is usable."""
    city = to_text(city_value)
    region = to_text(region_value)
    country = to_text(country_value)

    if not city or not country:
        return "", ""

    display_parts = [city]
    if region:
        display_parts.append(region)
    display_parts.append(country)

    display_value = ", ".join(display_parts)
    canonical_value = "|".join(part.lower() for part in display_parts)
    return display_value, canonical_value


def _get_safe_provider(normalized_record: NormalizedRecord) -> ProviderKind:
    """Return a safe provider enum for result objects."""
    if isinstance(normalized_record.provider, ProviderKind):
        return normalized_record.provider

    return ProviderKind.IPINFO


def _get_provider_text(normalized_record: NormalizedRecord) -> str:
    """Return a readable provider name for logs and metadata."""
    if isinstance(normalized_record.provider, ProviderKind):
        return normalized_record.provider.value

    return str(normalized_record.provider).strip()
