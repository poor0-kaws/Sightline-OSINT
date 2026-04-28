"""Strict relationship extraction from normalized records."""

from __future__ import annotations

import re
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
from backend.relationships.common import normalize_company_display
from backend.relationships.common import normalize_domain_value
from backend.relationships.common import normalize_email
from backend.relationships.common import normalize_ip_value
from backend.relationships.common import normalize_location_values
from backend.relationships.common import normalize_phone_number
from backend.relationships.common import normalize_text
from backend.relationships.schemas import EntityType
from backend.relationships.schemas import ExtractedRelationship
from backend.relationships.schemas import RelationshipType
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderKind


NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9]+")


def extract_relationships_from_normalized_record(normalized_record: NormalizedRecord) -> object:
    """Extract graph-ready relationships from one normalized record."""
    if normalized_record.status != FetchStatus.SUCCESS:
        return build_passthrough_result(normalized_record)

    if normalized_record.provider == ProviderKind.CRT_SH:
        return _extract_crt_sh_relationships(normalized_record)

    if normalized_record.provider == ProviderKind.MANUAL_INPUT:
        return _extract_manual_input_relationships(normalized_record)

    if normalized_record.provider == ProviderKind.WEBHOOK:
        return _extract_webhook_relationships(normalized_record)

    if normalized_record.provider == ProviderKind.IPINFO:
        return _extract_ipinfo_relationships(normalized_record)

    if normalized_record.provider == ProviderKind.NOMINATIM:
        return build_no_results_result(normalized_record)

    if normalized_record.provider == ProviderKind.CSV_UPLOAD:
        return build_no_results_result(normalized_record)

    if normalized_record.provider == ProviderKind.OPENSKY:
        return build_no_results_result(normalized_record)

    return build_error_result(
        normalized_record,
        code=ErrorCode.RELATIONSHIP_UNSUPPORTED_PROVIDER,
        message=f"No relationship extractor exists for provider: {_provider_text(normalized_record.provider)}",
    )


def _extract_crt_sh_relationships(normalized_record: NormalizedRecord) -> object:
    """Extract certificate -> domain and certificate -> issuer edges."""
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
            message="crt.sh normalized data must include a certificates list.",
        )

    relationships: list[ExtractedRelationship] = []
    for certificate_index, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            return build_error_result(
                normalized_record,
                code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
                message="Each crt.sh certificate item must be a dictionary.",
            )

        certificate_entity = build_entity_reference(
            record_scope=normalized_record.raw_record_id,
            entity_type=EntityType.CERTIFICATE,
            canonical_value=_certificate_canonical_value(certificate, certificate_index),
            display_value=_certificate_display_value(certificate, certificate_index),
        )

        for domain_value in _unique_certificate_domains(certificate):
            domain_entity = build_entity_reference(
                record_scope=normalized_record.raw_record_id,
                entity_type=EntityType.DOMAIN,
                canonical_value=domain_value,
                display_value=domain_value,
            )
            relationships.append(
                build_relationship(
                    relationship_id=f"{normalized_record.raw_record_id}:cert-domain:{certificate_index}:{domain_value}",
                    relationship_type=RelationshipType.CERTIFICATE_MENTIONS_DOMAIN,
                    from_entity=certificate_entity,
                    to_entity=domain_entity,
                    confidence_percent=95,
                    evidence_record_id=normalized_record.raw_record_id,
                )
            )

        issuer_display = normalize_text(certificate.get("issuer_name"))
        if issuer_display:
            issuer_entity = build_entity_reference(
                record_scope=normalized_record.raw_record_id,
                entity_type=EntityType.ISSUER,
                canonical_value=_normalize_text_key(issuer_display),
                display_value=issuer_display,
            )
            relationships.append(
                build_relationship(
                    relationship_id=f"{normalized_record.raw_record_id}:cert-issuer:{certificate_index}",
                    relationship_type=RelationshipType.CERTIFICATE_ISSUED_BY,
                    from_entity=certificate_entity,
                    to_entity=issuer_entity,
                    confidence_percent=95,
                    evidence_record_id=normalized_record.raw_record_id,
                )
            )

    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_manual_input_relationships(normalized_record: NormalizedRecord) -> object:
    """Extract person -> email/phone/company edges from manual input."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="Manual input normalized data must be a dictionary before relationship extraction.",
        )

    fields = normalized_record.normalized_data.get("fields")
    if not isinstance(fields, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="Manual input normalized data must include a fields dictionary.",
        )

    return _extract_person_contact_relationships(
        normalized_record,
        fields=fields,
        scope_label="manual",
    )


def _extract_webhook_relationships(normalized_record: NormalizedRecord) -> object:
    """Extract person-like webhook relationships when the payload is rich enough."""
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
            message="Webhook normalized data must include a payload dictionary.",
        )

    return _extract_person_contact_relationships(
        normalized_record,
        fields=payload,
        scope_label="webhook",
    )


def _extract_ipinfo_relationships(normalized_record: NormalizedRecord) -> object:
    """Extract IP -> organization and IP -> location edges from IPinfo data."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_error_result(
            normalized_record,
            code=ErrorCode.RELATIONSHIP_BAD_NORMALIZED_DATA,
            message="IPinfo normalized data must be a dictionary before relationship extraction.",
        )

    ip_value = normalize_ip_value(normalized_record.normalized_data.get("ip_address"))
    if not ip_value:
        return build_no_results_result(normalized_record)

    organization_display = normalize_company_display(normalized_record.normalized_data.get("organization"))
    organization_canonical = normalize_company_canonical(normalized_record.normalized_data.get("organization"))
    location_display, location_canonical = normalize_location_values(
        normalized_record.normalized_data.get("city"),
        normalized_record.normalized_data.get("region"),
        normalized_record.normalized_data.get("country"),
    )

    ip_entity = build_entity_reference(
        record_scope=normalized_record.raw_record_id,
        entity_type=EntityType.IP,
        canonical_value=ip_value,
        display_value=ip_value,
    )

    relationships: list[ExtractedRelationship] = []

    if organization_display and organization_canonical:
        organization_entity = build_entity_reference(
            record_scope=normalized_record.raw_record_id,
            entity_type=EntityType.ORGANIZATION,
            canonical_value=organization_canonical,
            display_value=organization_display,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{normalized_record.raw_record_id}:ip-org:{organization_canonical}",
                relationship_type=RelationshipType.IP_BELONGS_TO_ORGANIZATION,
                from_entity=ip_entity,
                to_entity=organization_entity,
                confidence_percent=90,
                evidence_record_id=normalized_record.raw_record_id,
            )
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
                relationship_id=f"{normalized_record.raw_record_id}:ip-location:{_slugify(location_canonical)}",
                relationship_type=RelationshipType.IP_LOCATED_IN,
                from_entity=ip_entity,
                to_entity=location_entity,
                confidence_percent=80,
                evidence_record_id=normalized_record.raw_record_id,
            )
        )

    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _extract_person_contact_relationships(
    normalized_record: NormalizedRecord,
    *,
    fields: dict[str, Any],
    scope_label: str,
) -> object:
    """Extract strict person-contact relationships from one mapping."""
    person_name = _first_text_value(fields, "full_name", "person_name", "name")
    if not person_name:
        return build_no_results_result(normalized_record)

    person_entity = build_entity_reference(
        record_scope=normalized_record.raw_record_id,
        entity_type=EntityType.PERSON,
        canonical_value=_normalize_text_key(person_name),
        display_value=person_name,
    )

    relationships: list[ExtractedRelationship] = []

    first_email = _first_valid_email(fields)
    if first_email:
        email_entity = build_entity_reference(
            record_scope=normalized_record.raw_record_id,
            entity_type=EntityType.EMAIL,
            canonical_value=first_email,
            display_value=first_email,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{normalized_record.raw_record_id}:{scope_label}:email:{_slugify(first_email)}",
                relationship_type=RelationshipType.PERSON_USES_EMAIL,
                from_entity=person_entity,
                to_entity=email_entity,
                confidence_percent=90,
                evidence_record_id=normalized_record.raw_record_id,
            )
        )

    first_phone = _first_valid_phone(fields)
    if first_phone:
        phone_entity = build_entity_reference(
            record_scope=normalized_record.raw_record_id,
            entity_type=EntityType.PHONE,
            canonical_value=first_phone,
            display_value=first_phone,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{normalized_record.raw_record_id}:{scope_label}:phone:{first_phone}",
                relationship_type=RelationshipType.PERSON_USES_PHONE,
                from_entity=person_entity,
                to_entity=phone_entity,
                confidence_percent=90,
                evidence_record_id=normalized_record.raw_record_id,
            )
        )

    company_display = normalize_company_display(_first_text_value(fields, "company_name", "company", "organization", "org"))
    company_canonical = normalize_company_canonical(company_display)
    if company_display and company_canonical:
        company_entity = build_entity_reference(
            record_scope=normalized_record.raw_record_id,
            entity_type=EntityType.COMPANY,
            canonical_value=company_canonical,
            display_value=company_display,
        )
        relationships.append(
            build_relationship(
                relationship_id=f"{normalized_record.raw_record_id}:{scope_label}:company:{_slugify(company_canonical)}",
                relationship_type=RelationshipType.PERSON_ASSOCIATED_WITH_COMPANY,
                from_entity=person_entity,
                to_entity=company_entity,
                confidence_percent=75,
                evidence_record_id=normalized_record.raw_record_id,
            )
        )

    if not relationships:
        return build_no_results_result(normalized_record)

    return build_success_result(normalized_record, relationships=relationships)


def _unique_certificate_domains(certificate: dict[str, Any]) -> list[str]:
    """Return clean unique domains from one certificate bundle."""
    raw_values: list[str] = []

    common_name = certificate.get("common_name")
    if isinstance(common_name, str):
        stripped_value = common_name.strip()
        if stripped_value:
            raw_values.append(stripped_value)

    name_value = certificate.get("name_value")
    if isinstance(name_value, str):
        for line in name_value.splitlines():
            stripped_value = line.strip()
            if stripped_value:
                raw_values.append(stripped_value)

    domains: list[str] = []
    seen_domains: set[str] = set()
    for raw_value in raw_values:
        domain_value = normalize_domain_value(raw_value)
        if not domain_value or domain_value in seen_domains:
            continue

        seen_domains.add(domain_value)
        domains.append(domain_value)

    return domains


def _certificate_canonical_value(certificate: dict[str, Any], certificate_index: int) -> str:
    """Build a stable certificate key from the best available fields."""
    common_name = normalize_domain_value(certificate.get("common_name"))
    not_before = normalize_text(certificate.get("not_before"))
    if common_name and not_before:
        return f"{common_name}|{not_before}"

    if common_name:
        return common_name

    if not_before:
        return not_before

    return f"certificate-{certificate_index}"


def _certificate_display_value(certificate: dict[str, Any], certificate_index: int) -> str:
    """Build a readable certificate label."""
    common_name = normalize_text(certificate.get("common_name"))
    if common_name:
        return common_name

    not_before = normalize_text(certificate.get("not_before"))
    if not_before:
        return not_before

    return f"certificate-{certificate_index}"


def _first_valid_email(fields: dict[str, Any]) -> str:
    """Return the first usable personal email from one mapping."""
    seen_emails: set[str] = set()
    for value in _collect_text_values(fields, "emails", "email"):
        normalized_email = normalize_email(value)
        if not normalized_email:
            continue

        if normalized_email in seen_emails:
            continue

        if is_role_based_email(normalized_email):
            continue

        if is_placeholder_email(normalized_email):
            continue

        seen_emails.add(normalized_email)
        return normalized_email

    return ""


def _first_valid_phone(fields: dict[str, Any]) -> str:
    """Return the first usable phone number from one mapping."""
    seen_phone_numbers: set[str] = set()
    for value in _collect_text_values(fields, "phone_numbers", "phone"):
        normalized_phone = normalize_phone_number(value)
        if not normalized_phone:
            continue

        if normalized_phone in seen_phone_numbers:
            continue

        if is_placeholder_phone_number(normalized_phone):
            continue

        seen_phone_numbers.add(normalized_phone)
        return normalized_phone

    return ""


def _collect_text_values(fields: dict[str, Any], *keys: str) -> list[str]:
    """Collect strings or string-list values from one mapping."""
    values: list[str] = []
    for key in keys:
        value = fields.get(key)
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value:
                values.append(stripped_value)
            continue

        if not isinstance(value, list):
            continue

        for item in value:
            if not isinstance(item, str):
                continue

            stripped_value = item.strip()
            if stripped_value:
                values.append(stripped_value)

    return values


def _first_text_value(fields: dict[str, Any], *keys: str) -> str:
    """Return the first clean string found under any of the given keys."""
    for key in keys:
        value = fields.get(key)
        if not isinstance(value, str):
            continue

        stripped_value = value.strip()
        if stripped_value:
            return stripped_value

    return ""


def _normalize_text_key(value: str) -> str:
    """Turn a free-text label into a stable comparison key."""
    cleaned_value = value.strip().lower()
    if not cleaned_value:
        return ""

    cleaned_value = NON_ALPHANUMERIC_PATTERN.sub(" ", cleaned_value)
    cleaned_value = re.sub(r"\s+", " ", cleaned_value).strip()
    return cleaned_value


def _slugify(value: str) -> str:
    """Turn a value into a stable id fragment."""
    cleaned_value = _normalize_text_key(value)
    if not cleaned_value:
        return "unknown"

    return cleaned_value.replace(" ", "-")


def _provider_text(provider: object) -> str:
    """Return a readable provider label."""
    if isinstance(provider, ProviderKind):
        return provider.value

    return str(provider).strip() or "unknown"
