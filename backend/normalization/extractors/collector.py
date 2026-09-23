"""Shared artifact collector and canonicalization helpers for extractors."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedEntity
from backend.normalization.schemas import NormalizedEvidence
from backend.normalization.schemas import NormalizedRecord
from backend.normalization.schemas import NormalizedRelationshipCandidate
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.utils.identifiers import normalize_domain
from backend.utils.identifiers import normalize_email
from backend.utils.identifiers import normalize_ipv4
from backend.utils.text import normalize_free_text
from backend.utils.text import to_text


def build_output_record(
    normalized_record: NormalizedRecord,
    *,
    entities: list[NormalizedEntity] | None = None,
    evidence: list[NormalizedEvidence] | None = None,
    relationship_candidates: list[NormalizedRelationshipCandidate] | None = None,
) -> NormalizedRecord:
    """Build one normalized record with shared artifact lists attached."""
    return NormalizedRecord(
        provider=normalized_record.provider,
        source_type=normalized_record.source_type,
        case_id=normalized_record.case_id,
        raw_record_id=normalized_record.raw_record_id,
        query=normalized_record.query,
        status=normalized_record.status,
        error=normalized_record.error,
        normalized_data=normalized_record.normalized_data,
        metadata=dict(normalized_record.metadata),
        entities=list(entities or []),
        evidence=list(evidence or []),
        relationship_candidates=list(relationship_candidates or []),
    )


def build_bad_normalized_data_record(
    normalized_record: NormalizedRecord,
    *,
    message: str,
) -> NormalizedRecord:
    """Return a clean shared-extraction error for malformed normalized data."""
    metadata = dict(normalized_record.metadata)
    metadata["failed_stage"] = "shared_artifact_extraction"
    return NormalizedRecord(
        provider=normalized_record.provider,
        source_type=normalized_record.source_type,
        case_id=normalized_record.case_id,
        raw_record_id=normalized_record.raw_record_id,
        query=normalized_record.query,
        status=FetchStatus.ERROR,
        error=ProviderError(
            code=ErrorCode.NORMALIZATION_BAD_NORMALIZED_DATA.value,
            message=message,
        ),
        normalized_data=None,
        metadata=metadata,
        entities=[],
        evidence=[],
        relationship_candidates=[],
    )


class ArtifactCollector:
    """Tiny helper that deduplicates shared extraction output."""

    def __init__(self, normalized_record: NormalizedRecord) -> None:
        self.normalized_record = normalized_record
        self.entities: list[NormalizedEntity] = []
        self.evidence: list[NormalizedEvidence] = []
        self.relationship_candidates: list[NormalizedRelationshipCandidate] = []
        self._entity_keys: set[tuple[str, str]] = set()
        self._evidence_keys: set[tuple[str, str, str]] = set()
        self._relationship_keys: set[tuple[str, str, str, str, str]] = set()

    def build(self) -> NormalizedRecord:
        """Return the final enriched normalized record."""
        return build_output_record(
            self.normalized_record,
            entities=self.entities,
            evidence=self.evidence,
            relationship_candidates=self.relationship_candidates,
        )

    def add_person_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add a person entity when the value is usable."""
        canonical_value = normalize_free_text(value)
        if not canonical_value:
            return ""

        display_value = to_text(value)
        self._add_entity("person", canonical_value, display_value, metadata=metadata)
        self._add_evidence("person", canonical_value, "person_field", detail, metadata=metadata)
        return canonical_value

    def add_email_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add an email entity when the value is usable."""
        canonical_value = normalize_email(value)
        if not canonical_value:
            return ""

        self._add_entity("email", canonical_value, canonical_value, metadata=metadata)
        self._add_evidence("email", canonical_value, "email_field", detail, metadata=metadata)
        return canonical_value

    def add_domain_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add a domain entity when the value is usable."""
        canonical_value = normalize_domain(value, strip_wildcard=True)
        if not canonical_value:
            return ""

        display_value = to_text(value) or canonical_value
        self._add_entity("domain", canonical_value, display_value, metadata=metadata)
        self._add_evidence("domain", canonical_value, "domain_field", detail, metadata=metadata)
        return canonical_value

    def add_ip_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add an IP entity when the value is usable."""
        canonical_value = normalize_ipv4(value)
        if not canonical_value:
            return ""

        self._add_entity("ip", canonical_value, canonical_value, metadata=metadata)
        self._add_evidence("ip", canonical_value, "ip_field", detail, metadata=metadata)
        return canonical_value

    def add_organization_entity(
        self,
        value: object,
        *,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add an organization entity when the value is usable."""
        canonical_value = normalize_free_text(value)
        if not canonical_value:
            return ""

        display_value = to_text(value) or canonical_value
        self._add_entity("organization", canonical_value, display_value, metadata=metadata)
        self._add_evidence("organization", canonical_value, "organization_field", detail, metadata=metadata)
        return canonical_value

    def add_company_entity(
        self,
        value: object,
        *,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a company entity when the value is usable."""
        canonical_value = normalize_free_text(value)
        if not canonical_value:
            return ""

        display_value = to_text(value) or canonical_value
        self._add_entity("company", canonical_value, display_value, metadata=metadata)
        self._add_evidence("company", canonical_value, "company_field", detail, metadata=metadata)
        return canonical_value

    def add_place_entity(
        self,
        *,
        city: str = "",
        region: str = "",
        country: str = "",
        display_name: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a place entity when there is enough location information."""
        canonical_value = canonical_place(
            city=city,
            region=region,
            country=country,
            display_name=display_name,
            latitude=latitude,
            longitude=longitude,
        )
        if not canonical_value:
            return ""

        display_value = display_name.strip() if display_name.strip() else canonical_value
        entity_metadata = dict(metadata or {})
        if city:
            entity_metadata["city"] = city
        if region:
            entity_metadata["region"] = region
        if country:
            entity_metadata["country"] = country
        if latitude is not None:
            entity_metadata["latitude"] = latitude
        if longitude is not None:
            entity_metadata["longitude"] = longitude

        self._add_entity("place", canonical_value, display_value, metadata=entity_metadata)
        self._add_evidence("place", canonical_value, "place_field", detail, metadata=entity_metadata)
        return canonical_value

    def add_aircraft_entity(
        self,
        value: object,
        *,
        callsign: str = "",
        origin_country: str = "",
        longitude: float | None = None,
        latitude: float | None = None,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add an aircraft entity when the value is usable."""
        canonical_value = canonical_aircraft(value)
        if not canonical_value:
            return ""

        entity_metadata = dict(metadata or {})
        if callsign:
            entity_metadata["callsign"] = callsign
        if origin_country:
            entity_metadata["origin_country"] = origin_country
        if latitude is not None:
            entity_metadata["latitude"] = latitude
        if longitude is not None:
            entity_metadata["longitude"] = longitude

        self._add_entity("aircraft", canonical_value, to_text(value) or canonical_value, metadata=entity_metadata)
        self._add_evidence("aircraft", canonical_value, "aircraft_field", detail, metadata=entity_metadata)
        return canonical_value

    def add_relationship_if_present(
        self,
        *,
        relationship_type: str,
        source_entity_type: str,
        source_value: str,
        target_entity_type: str,
        target_value: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add one relationship candidate when both sides are present."""
        if not relationship_type.strip():
            return

        if not source_value or not target_value:
            return

        relationship_key = (
            relationship_type,
            source_entity_type,
            source_value,
            target_entity_type,
            target_value,
        )
        if relationship_key in self._relationship_keys:
            return

        self._relationship_keys.add(relationship_key)
        self.relationship_candidates.append(
            NormalizedRelationshipCandidate(
                relationship_type=relationship_type,
                source_entity_type=source_entity_type,
                source_canonical_value=source_value,
                target_entity_type=target_entity_type,
                target_canonical_value=target_value,
                metadata=dict(metadata or {}),
            )
        )

    def _add_entity(
        self,
        entity_type: str,
        canonical_value: str,
        display_value: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add one deduplicated entity."""
        entity_key = (entity_type, canonical_value)
        if entity_key in self._entity_keys:
            return

        self._entity_keys.add(entity_key)
        self.entities.append(
            NormalizedEntity(
                entity_type=entity_type,
                canonical_value=canonical_value,
                display_value=display_value,
                metadata=dict(metadata or {}),
            )
        )

    def _add_evidence(
        self,
        entity_type: str,
        canonical_value: str,
        evidence_type: str,
        detail: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add one deduplicated evidence item."""
        evidence_key = (entity_type, canonical_value, detail)
        if evidence_key in self._evidence_keys:
            return

        self._evidence_keys.add(evidence_key)
        self.evidence.append(
            NormalizedEvidence(
                evidence_type=evidence_type,
                entity_type=entity_type,
                canonical_value=canonical_value,
                detail=detail,
                source_provider=self.normalized_record.provider,
                source_record_id=self.normalized_record.raw_record_id,
                source_query=self.normalized_record.query,
                metadata=dict(metadata or {}),
            )
        )


def extract_certificate_domains(certificate: dict[str, Any]) -> list[str]:
    """Return cleaned, unique domain values from one normalized certificate."""
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
        canonical_value = normalize_domain(raw_value, strip_wildcard=True)
        if not canonical_value:
            continue

        if canonical_value in seen_domains:
            continue

        seen_domains.add(canonical_value)
        domains.append(canonical_value)

    return domains


def canonical_aircraft(value: object) -> str:
    """Return a clean comparable aircraft id value."""
    if not isinstance(value, str):
        return ""

    return value.strip().lower()


def canonical_place(
    *,
    city: str = "",
    region: str = "",
    country: str = "",
    display_name: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    """Return a clean comparable place value from names or coordinates."""
    display_canonical = normalize_free_text(display_name)
    if display_canonical:
        return display_canonical

    place_parts = [city, region, country]
    cleaned_parts = [normalize_free_text(part) for part in place_parts if normalize_free_text(part)]
    if cleaned_parts:
        return "|".join(cleaned_parts)

    if latitude is None or longitude is None:
        return ""

    return f"{latitude:.4f},{longitude:.4f}"
