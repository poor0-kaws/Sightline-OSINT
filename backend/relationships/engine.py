"""Provider-specific relationship extractors and their provider registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.relationships.common import build_entity_reference
from backend.relationships.common import build_error_result
from backend.relationships.common import build_no_results_result
from backend.relationships.common import build_passthrough_result
from backend.relationships.common import build_relationship
from backend.relationships.common import build_success_result
from backend.relationships.common import is_placeholder_email
from backend.relationships.common import is_placeholder_phone_number
from backend.relationships.common import is_role_based_email
from backend.relationships.common import normalize_company_canonical
from backend.relationships.common import normalize_email
from backend.relationships.common import normalize_location_values
from backend.relationships.common import normalize_phone_number
from backend.relationships.schemas import EntityType
from backend.relationships.schemas import ExtractedRelationship
from backend.relationships.schemas import RelationshipExtractionResult
from backend.relationships.schemas import RelationshipType
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderKind
from backend.utils.identifiers import normalize_domain
from backend.utils.identifiers import normalize_ipv4
from backend.utils.text import collect_text_values
from backend.utils.text import first_text_value
from backend.utils.text import to_text


PERSON_EMAIL_CONFIDENCE = 95
PERSON_PHONE_CONFIDENCE = 95
PERSON_COMPANY_CONFIDENCE = 80
IP_ORG_CONFIDENCE = 90
IP_LOCATION_CONFIDENCE = 85
CERTIFICATE_DOMAIN_CONFIDENCE = 95
CERTIFICATE_ISSUER_CONFIDENCE = 90
AIRCRAFT_PLACE_CONFIDENCE = 85


def extract_relationships_from_normalized_record(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Route one normalized record to the right relationship extractor."""
    if normalized_record.status != FetchStatus.SUCCESS:
        return build_passthrough_result(normalized_record)

    extractor = RELATIONSHIP_EXTRACTOR_BY_PROVIDER.get(normalized_record.provider)
    if extractor is not None:
        return extractor(normalized_record)

    return build_error_result(
        normalized_record,
        code=ErrorCode.RELATIONSHIP_UNSUPPORTED_PROVIDER,
        message="No relationship extractor exists for this provider.",
    )


def _extract_ipinfo_relationships(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Turn one IPinfo normalized record into a small set of graph edges."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="IPinfo normalized data must be a dictionary before relationship extraction.",
        )

    ip_value = normalize_ipv4(normalized_record.normalized_data.get("ip_address"))
    if not ip_value:
        return build_no_results_result(normalized_record)

    ip_entity = build_entity_reference(
        record_scope=normalized_record.raw_record_id,
        entity_type=EntityType.IP,
        canonical_value=ip_value,
        display_value=ip_value,
    )

    relationships: list[ExtractedRelationship] = []

    organization_display = to_text(normalized_record.normalized_data.get("organization"))
    organization_canonical = normalize_company_canonical(organization_display)
    if organization_display and organization_canonical:
        organization_entity = build_entity_reference(
            record_scope=normalized_record.raw_record_id,
            entity_type=EntityType.ORGANIZATION,
            canonical_value=organization_canonical,
            display_value=organization_display,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{normalized_record.raw_record_id}:ip-org",
                relationship_type=RelationshipType.IP_BELONGS_TO_ORGANIZATION,
                from_entity=ip_entity,
                to_entity=organization_entity,
                confidence_percent=IP_ORG_CONFIDENCE,
                evidence_record_id=normalized_record.raw_record_id,
            )
        )

    location_display, location_canonical = normalize_location_values(
        normalized_record.normalized_data.get("city"),
        normalized_record.normalized_data.get("region"),
        normalized_record.normalized_data.get("country"),
    )
    if location_display and location_canonical:
        location_entity = build_entity_reference(
            record_scope=normalized_record.raw_record_id,
            entity_type=EntityType.LOCATION,
            canonical_value=location_canonical,
            display_value=location_display,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{normalized_record.raw_record_id}:ip-location",
                relationship_type=RelationshipType.IP_LOCATED_IN,
                from_entity=ip_entity,
                to_entity=location_entity,
                confidence_percent=IP_LOCATION_CONFIDENCE,
                evidence_record_id=normalized_record.raw_record_id,
            )
        )

    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_crt_sh_relationships(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Turn one crt.sh normalized record into certificate-domain edges."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="crt.sh normalized data must be a dictionary before relationship extraction.",
        )

    certificates = normalized_record.normalized_data.get("certificates")
    if not isinstance(certificates, list):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="crt.sh normalized data must include a certificates list before relationship extraction.",
        )

    relationships: list[ExtractedRelationship] = []

    for certificate_index, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            return build_error_result(
                normalized_record,
                code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
                message="Each crt.sh certificate must be a dictionary before relationship extraction.",
            )

        certificate_scope = f"{normalized_record.raw_record_id}:certificate:{certificate_index}"
        certificate_entity = build_entity_reference(
            record_scope=certificate_scope,
            entity_type=EntityType.CERTIFICATE,
            canonical_value=certificate_scope,
            display_value=to_text(certificate.get("common_name")) or f"certificate-{certificate_index}",
        )

        seen_domains: set[str] = set()
        for domain_value in _extract_certificate_domains(certificate):
            if domain_value in seen_domains:
                continue

            seen_domains.add(domain_value)
            domain_entity = build_entity_reference(
                record_scope=certificate_scope,
                entity_type=EntityType.DOMAIN,
                canonical_value=domain_value,
                display_value=domain_value,
            )
            relationships.append(
                build_relationship(
                    relationship_id=f"{certificate_scope}:domain:{len(seen_domains)}",
                    relationship_type=RelationshipType.CERTIFICATE_MENTIONS_DOMAIN,
                    from_entity=certificate_entity,
                    to_entity=domain_entity,
                    confidence_percent=CERTIFICATE_DOMAIN_CONFIDENCE,
                    evidence_record_id=normalized_record.raw_record_id,
                    metadata={"certificate_index": certificate_index},
                )
            )

        issuer_display = to_text(certificate.get("issuer_name"))
        issuer_canonical = normalize_company_canonical(issuer_display)
        if issuer_display and issuer_canonical:
            issuer_entity = build_entity_reference(
                record_scope=certificate_scope,
                entity_type=EntityType.ISSUER,
                canonical_value=issuer_canonical,
                display_value=issuer_display,
            )
            relationships.append(
                build_relationship(
                    relationship_id=f"{certificate_scope}:issuer",
                    relationship_type=RelationshipType.CERTIFICATE_ISSUED_BY,
                    from_entity=certificate_entity,
                    to_entity=issuer_entity,
                    confidence_percent=CERTIFICATE_ISSUER_CONFIDENCE,
                    evidence_record_id=normalized_record.raw_record_id,
                    metadata={"certificate_index": certificate_index},
                )
            )

    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_manual_input_relationships(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Extract person contact edges from one manual-input normalized record."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="Manual-input normalized data must be a dictionary before relationship extraction.",
        )

    fields = normalized_record.normalized_data.get("fields")
    if not isinstance(fields, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="Manual-input normalized data must include a fields dictionary before relationship extraction.",
        )

    relationships = _extract_person_like_relationships(
        record_scope=f"{normalized_record.raw_record_id}:person",
        evidence_record_id=normalized_record.raw_record_id,
        fields=fields,
    )
    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_webhook_relationships(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Extract person contact edges from one webhook payload when it is clear enough."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="Webhook normalized data must be a dictionary before relationship extraction.",
        )

    payload = normalized_record.normalized_data.get("payload")
    if not isinstance(payload, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="Webhook normalized data must include a payload dictionary before relationship extraction.",
        )

    relationships = _extract_person_like_relationships(
        record_scope=f"{normalized_record.raw_record_id}:payload",
        evidence_record_id=normalized_record.raw_record_id,
        fields=payload,
    )
    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_csv_upload_relationships(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Extract person contact edges from CSV rows when rows are clear enough."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="CSV-upload normalized data must be a dictionary before relationship extraction.",
        )

    rows = normalized_record.normalized_data.get("rows")
    if not isinstance(rows, list):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="CSV-upload normalized data must include a rows list before relationship extraction.",
        )

    relationships: list[ExtractedRelationship] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            return build_error_result(
                normalized_record,
                code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
                message="Each CSV-upload row must be a dictionary before relationship extraction.",
            )

        relationships.extend(
            _extract_person_like_relationships(
                record_scope=f"{normalized_record.raw_record_id}:row:{row_index}",
                evidence_record_id=normalized_record.raw_record_id,
                fields=row,
            )
        )

    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_opensky_relationships(normalized_record: NormalizedRecord) -> RelationshipExtractionResult:
    """Extract aircraft-location edges from OpenSky shared candidates."""
    relationships: list[ExtractedRelationship] = []

    for index, candidate in enumerate(normalized_record.relationship_candidates):
        relationship_type = to_text(candidate.relationship_type)
        if relationship_type != "observed_over":
            continue

        if candidate.source_entity_type != "aircraft" or candidate.target_entity_type != "place":
            continue

        aircraft_value = to_text(candidate.source_canonical_value)
        place_value = to_text(candidate.target_canonical_value)
        if not aircraft_value or not place_value:
            continue

        aircraft_entity = build_entity_reference(
            record_scope=f"{normalized_record.raw_record_id}:opensky:{index}",
            entity_type=EntityType.AIRCRAFT,
            canonical_value=aircraft_value,
            display_value=aircraft_value,
        )
        place_entity = build_entity_reference(
            record_scope=f"{normalized_record.raw_record_id}:opensky:{index}",
            entity_type=EntityType.PLACE,
            canonical_value=place_value,
            display_value=place_value,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{normalized_record.raw_record_id}:aircraft-place:{index}",
                relationship_type=RelationshipType.AIRCRAFT_OBSERVED_OVER,
                from_entity=aircraft_entity,
                to_entity=place_entity,
                confidence_percent=AIRCRAFT_PLACE_CONFIDENCE,
                evidence_record_id=normalized_record.raw_record_id,
                metadata=dict(candidate.metadata),
            )
        )

    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_person_like_relationships(
    *,
    record_scope: str,
    evidence_record_id: str,
    fields: dict[str, Any],
) -> list[ExtractedRelationship]:
    """Build person-contact edges only when the field bundle is clear enough."""
    full_name = first_text_value(fields, "full_name", "name")
    usable_emails = _extract_usable_emails(fields)
    usable_phone_numbers = _extract_usable_phone_numbers(fields)
    company_display = first_text_value(fields, "company_name", "company")
    company_canonical = normalize_company_canonical(company_display)

    has_anchor = bool(full_name or usable_emails or usable_phone_numbers)
    if not has_anchor:
        return []

    person_display = full_name or "Unnamed person"
    person_canonical = full_name.lower() if full_name else record_scope
    person_entity = build_entity_reference(
        record_scope=record_scope,
        entity_type=EntityType.PERSON,
        canonical_value=person_canonical,
        display_value=person_display,
    )

    relationships: list[ExtractedRelationship] = []

    for email_index, email_value in enumerate(sorted(usable_emails), start=1):
        email_entity = build_entity_reference(
            record_scope=record_scope,
            entity_type=EntityType.EMAIL,
            canonical_value=email_value,
            display_value=email_value,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{record_scope}:email:{email_index}",
                relationship_type=RelationshipType.PERSON_USES_EMAIL,
                from_entity=person_entity,
                to_entity=email_entity,
                confidence_percent=PERSON_EMAIL_CONFIDENCE,
                evidence_record_id=evidence_record_id,
            )
        )

    for phone_index, phone_value in enumerate(sorted(usable_phone_numbers), start=1):
        phone_entity = build_entity_reference(
            record_scope=record_scope,
            entity_type=EntityType.PHONE,
            canonical_value=phone_value,
            display_value=phone_value,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{record_scope}:phone:{phone_index}",
                relationship_type=RelationshipType.PERSON_USES_PHONE,
                from_entity=person_entity,
                to_entity=phone_entity,
                confidence_percent=PERSON_PHONE_CONFIDENCE,
                evidence_record_id=evidence_record_id,
            )
        )

    if company_display and company_canonical:
        company_entity = build_entity_reference(
            record_scope=record_scope,
            entity_type=EntityType.COMPANY,
            canonical_value=company_canonical,
            display_value=company_display,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{record_scope}:company",
                relationship_type=RelationshipType.PERSON_ASSOCIATED_WITH_COMPANY,
                from_entity=person_entity,
                to_entity=company_entity,
                confidence_percent=PERSON_COMPANY_CONFIDENCE,
                evidence_record_id=evidence_record_id,
            )
        )

    return relationships


def _extract_certificate_domains(certificate: dict[str, Any]) -> list[str]:
    """Pull all usable domain strings out of one normalized certificate."""
    raw_domain_values: list[str] = []

    common_name = to_text(certificate.get("common_name"))
    if common_name:
        raw_domain_values.append(common_name)

    name_value = to_text(certificate.get("name_value"))
    if name_value:
        for item in name_value.splitlines():
            cleaned_value = to_text(item)
            if not cleaned_value:
                continue
            raw_domain_values.append(cleaned_value)

    normalized_domains: list[str] = []
    for raw_domain_value in raw_domain_values:
        normalized_domain = normalize_domain(raw_domain_value, strip_wildcard=True)
        if not normalized_domain:
            continue
        normalized_domains.append(normalized_domain)

    return normalized_domains


def _extract_usable_emails(fields: dict[str, Any]) -> set[str]:
    """Return personal-looking email addresses from one field bundle."""
    usable_emails: set[str] = set()

    for email_value in collect_text_values(fields, "emails", "email"):
        normalized_email = normalize_email(email_value)
        if not normalized_email:
            continue

        if is_role_based_email(normalized_email):
            continue

        if is_placeholder_email(normalized_email):
            continue

        usable_emails.add(normalized_email)

    return usable_emails


def _extract_usable_phone_numbers(fields: dict[str, Any]) -> set[str]:
    """Return real-looking phone numbers from one field bundle."""
    usable_phone_numbers: set[str] = set()

    for phone_value in collect_text_values(fields, "phone_numbers", "phones", "phone"):
        normalized_phone = normalize_phone_number(phone_value)
        if not normalized_phone:
            continue

        if is_placeholder_phone_number(normalized_phone):
            continue

        usable_phone_numbers.add(normalized_phone)

    return usable_phone_numbers


RelationshipExtractor = Callable[[NormalizedRecord], RelationshipExtractionResult]

RELATIONSHIP_EXTRACTOR_BY_PROVIDER: dict[ProviderKind, RelationshipExtractor] = {
    ProviderKind.IPINFO: _extract_ipinfo_relationships,
    ProviderKind.CRT_SH: _extract_crt_sh_relationships,
    ProviderKind.MANUAL_INPUT: _extract_manual_input_relationships,
    ProviderKind.WEBHOOK: _extract_webhook_relationships,
    ProviderKind.CSV_UPLOAD: _extract_csv_upload_relationships,
    ProviderKind.NOMINATIM: build_no_results_result,
    ProviderKind.OPENSKY: _extract_opensky_relationships,
}
