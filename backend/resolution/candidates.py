"""Helpers that turn normalized records into resolution match candidates."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.resolution.schemas import EntityType
from backend.resolution.schemas import MatchCandidate
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderKind
from backend.utils.validation import is_valid_domain_name
from backend.utils.validation import is_valid_ipv4_address


def build_match_candidates_from_normalized_record(normalized_record: NormalizedRecord) -> list[MatchCandidate]:
    """Build zero or more match candidates from one normalized record."""
    if normalized_record.status != FetchStatus.SUCCESS:
        return []

    if normalized_record.provider == ProviderKind.IPINFO:
        return _build_ipinfo_candidates(normalized_record)

    if normalized_record.provider == ProviderKind.CRT_SH:
        return _build_crt_sh_candidates(normalized_record)

    if normalized_record.provider == ProviderKind.MANUAL_INPUT:
        return _build_manual_input_candidates(normalized_record)

    return []


def build_domain_candidate(*, record_id: str, domain_value: str, display_value: str = "") -> MatchCandidate | None:
    """Build one exact-match-ready domain candidate when the value is valid."""
    canonical_domain = _normalize_domain_value(domain_value)
    if not canonical_domain:
        return None

    return MatchCandidate(
        record_id=record_id,
        entity_type=EntityType.DOMAIN,
        canonical_value=canonical_domain,
        display_value=display_value.strip() if isinstance(display_value, str) and display_value.strip() else canonical_domain,
        attributes={},
    )


def build_ip_candidate(*, record_id: str, ip_value: str, display_value: str = "") -> MatchCandidate | None:
    """Build one exact-match-ready IP candidate when the value is valid."""
    canonical_ip = _normalize_ip_value(ip_value)
    if not canonical_ip:
        return None

    return MatchCandidate(
        record_id=record_id,
        entity_type=EntityType.IP,
        canonical_value=canonical_ip,
        display_value=display_value.strip() if isinstance(display_value, str) and display_value.strip() else canonical_ip,
        attributes={},
    )


def build_person_candidate(*, record_id: str, fields: dict[str, Any]) -> MatchCandidate | None:
    """Build one person candidate when the field bundle clearly looks person-like."""
    if not isinstance(fields, dict):
        return None

    full_name = _first_text_value(fields, "full_name", "name")
    emails = _list_text_values(fields, "emails", "email")
    phone_numbers = _list_text_values(fields, "phone_numbers", "phones", "phone")
    company_name = _first_text_value(fields, "company_name", "company")
    city = _first_text_value(fields, "city")
    region = _first_text_value(fields, "region", "state")
    country = _first_text_value(fields, "country")

    if not any([full_name, emails, phone_numbers, company_name, city, region, country]):
        return None

    return MatchCandidate(
        record_id=record_id,
        entity_type=EntityType.PERSON,
        canonical_value=full_name.lower() if full_name else "",
        display_value=full_name,
        attributes={
            "full_name": full_name,
            "emails": emails,
            "phone_numbers": phone_numbers,
            "company_name": company_name,
            "city": city,
            "region": region,
            "country": country,
        },
    )


def _build_ipinfo_candidates(normalized_record: NormalizedRecord) -> list[MatchCandidate]:
    """Extract IP candidates from IPinfo normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return []

    ip_value = normalized_record.normalized_data.get("ip_address")
    candidate = build_ip_candidate(
        record_id=f"{normalized_record.raw_record_id}:ip",
        ip_value=ip_value if isinstance(ip_value, str) else "",
        display_value=ip_value if isinstance(ip_value, str) else "",
    )
    if candidate is None:
        return []

    return [candidate]


def _build_crt_sh_candidates(normalized_record: NormalizedRecord) -> list[MatchCandidate]:
    """Extract domain candidates from crt.sh normalized certificates."""
    if not isinstance(normalized_record.normalized_data, dict):
        return []

    certificates = normalized_record.normalized_data.get("certificates")
    if not isinstance(certificates, list):
        return []

    candidates: list[MatchCandidate] = []
    seen_domains: set[str] = set()

    for index, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            return []

        domain_values = _extract_certificate_domains(certificate)
        for domain_value in domain_values:
            if domain_value in seen_domains:
                continue

            seen_domains.add(domain_value)
            candidate = build_domain_candidate(
                record_id=f"{normalized_record.raw_record_id}:domain:{index}:{len(candidates)}",
                domain_value=domain_value,
                display_value=domain_value,
            )
            if candidate is None:
                continue

            candidates.append(candidate)

    return candidates


def _build_manual_input_candidates(normalized_record: NormalizedRecord) -> list[MatchCandidate]:
    """Extract person candidates from manual-input normalized output when fields are clear."""
    if not isinstance(normalized_record.normalized_data, dict):
        return []

    fields = normalized_record.normalized_data.get("fields")
    if not isinstance(fields, dict):
        return []

    candidate = build_person_candidate(
        record_id=f"{normalized_record.raw_record_id}:person",
        fields=fields,
    )
    if candidate is None:
        return []

    return [candidate]


def _extract_certificate_domains(certificate: dict[str, Any]) -> list[str]:
    """Pull domain values out of one normalized crt.sh certificate record."""
    domain_values: list[str] = []

    common_name = certificate.get("common_name")
    if isinstance(common_name, str):
        stripped_value = common_name.strip()
        if stripped_value:
            domain_values.append(stripped_value)

    name_value = certificate.get("name_value")
    if isinstance(name_value, str):
        for item in name_value.splitlines():
            stripped_value = item.strip()
            if stripped_value:
                domain_values.append(stripped_value)

    normalized_domains: list[str] = []
    for domain_value in domain_values:
        canonical_domain = _normalize_domain_value(domain_value)
        if not canonical_domain:
            continue

        normalized_domains.append(canonical_domain)

    return normalized_domains


def _normalize_domain_value(value: str) -> str:
    """Normalize a domain candidate into a stable exact-match value."""
    if not isinstance(value, str):
        return ""

    normalized_value = value.strip().lower()
    if not is_valid_domain_name(normalized_value):
        return ""

    return normalized_value


def _normalize_ip_value(value: str) -> str:
    """Normalize an IP candidate into a stable exact-match value."""
    if not isinstance(value, str):
        return ""

    normalized_value = value.strip()
    if not is_valid_ipv4_address(normalized_value):
        return ""

    return normalized_value


def _first_text_value(fields: dict[str, Any], *keys: str) -> str:
    """Return the first clean text value found under the given keys."""
    for key in keys:
        value = fields.get(key)
        if not isinstance(value, str):
            continue

        cleaned_value = value.strip()
        if cleaned_value:
            return cleaned_value

    return ""


def _list_text_values(fields: dict[str, Any], *keys: str) -> list[str]:
    """Return a flat list of clean text values from one or more field keys."""
    collected_values: list[str] = []

    for key in keys:
        value = fields.get(key)
        if isinstance(value, str):
            cleaned_value = value.strip()
            if cleaned_value:
                collected_values.append(cleaned_value)
            continue

        if not isinstance(value, list):
            continue

        for item in value:
            if not isinstance(item, str):
                continue

            cleaned_item = item.strip()
            if cleaned_item:
                collected_values.append(cleaned_item)

    return collected_values
