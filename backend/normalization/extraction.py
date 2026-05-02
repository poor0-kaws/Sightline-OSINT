"""Second-layer extraction of shared entities, evidence, and relationship candidates."""

from __future__ import annotations

import re
from typing import Any

from backend.normalization.schemas import NormalizedEntity
from backend.normalization.schemas import NormalizedEvidence
from backend.normalization.schemas import NormalizedRecord
from backend.normalization.schemas import NormalizedRelationshipCandidate
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.utils.validation import is_valid_domain_name
from backend.utils.validation import is_valid_ipv4_address


def extract_shared_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Add shared entities, evidence, and relationship candidates to one normalized record."""
    if normalized_record.status == FetchStatus.NO_RESULTS:
        return _build_output_record(normalized_record)

    if normalized_record.status != FetchStatus.SUCCESS:
        return _build_output_record(normalized_record)

    if normalized_record.provider == ProviderKind.IPINFO:
        return _extract_ipinfo_artifacts(normalized_record)

    if normalized_record.provider == ProviderKind.CRT_SH:
        return _extract_crt_sh_artifacts(normalized_record)

    if normalized_record.provider == ProviderKind.NOMINATIM:
        return _extract_nominatim_artifacts(normalized_record)

    if normalized_record.provider == ProviderKind.OPENSKY:
        return _extract_opensky_artifacts(normalized_record)

    if normalized_record.provider == ProviderKind.WEBHOOK:
        return _extract_webhook_artifacts(normalized_record)

    if normalized_record.provider == ProviderKind.CSV_UPLOAD:
        return _extract_csv_upload_artifacts(normalized_record)

    if normalized_record.provider == ProviderKind.MANUAL_INPUT:
        return _extract_manual_input_artifacts(normalized_record)

    return _build_output_record(normalized_record)


def _extract_ipinfo_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from IPinfo normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="IPinfo normalized data must be a dictionary before shared extraction.",
        )

    collector = _ArtifactCollector(normalized_record)

    ip_value = normalized_record.normalized_data.get("ip_address")
    organization_value = normalized_record.normalized_data.get("organization")
    as_domain = normalized_record.normalized_data.get("as_domain")
    city = _to_text(normalized_record.normalized_data.get("city"))
    region = _to_text(normalized_record.normalized_data.get("region"))
    country = _to_text(normalized_record.normalized_data.get("country"))

    collector.add_ip_entity(
        ip_value,
        detail="IPinfo provided this IP address.",
    )
    collector.add_organization_entity(
        organization_value,
        detail="IPinfo provided this organization value.",
    )
    collector.add_domain_entity(
        as_domain,
        detail="IPinfo Lite provided this ASN domain value.",
    )
    collector.add_place_entity(
        city=city,
        region=region,
        country=country,
        detail="IPinfo provided this location bundle.",
    )
    collector.add_relationship_if_present(
        relationship_type="associated_with",
        source_entity_type="ip",
        source_value=_canonical_ip(ip_value),
        target_entity_type="organization",
        target_value=_canonical_organization(organization_value),
    )
    collector.add_relationship_if_present(
        relationship_type="associated_with",
        source_entity_type="ip",
        source_value=_canonical_ip(ip_value),
        target_entity_type="domain",
        target_value=_canonical_domain(as_domain),
    )
    collector.add_relationship_if_present(
        relationship_type="located_in",
        source_entity_type="ip",
        source_value=_canonical_ip(ip_value),
        target_entity_type="place",
        target_value=_canonical_place(city=city, region=region, country=country),
    )

    return collector.build()


def _extract_crt_sh_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from crt.sh normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="crt.sh normalized data must be a dictionary before shared extraction.",
        )

    certificates = normalized_record.normalized_data.get("certificates")
    if not isinstance(certificates, list):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="crt.sh normalized data must include a certificates list before shared extraction.",
        )

    collector = _ArtifactCollector(normalized_record)

    for certificate_index, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            return _build_bad_normalized_data_record(
                normalized_record,
                message="Each crt.sh certificate must be a dictionary before shared extraction.",
            )

        issuer_name = certificate.get("issuer_name")
        issuer_canonical = _canonical_organization(issuer_name)
        collector.add_organization_entity(
            issuer_name,
            detail="crt.sh certificate issuer.",
            metadata={"certificate_index": certificate_index},
        )

        for domain_value in _extract_certificate_domains(certificate):
            collector.add_domain_entity(
                domain_value,
                detail="crt.sh certificate domain name.",
                metadata={"certificate_index": certificate_index},
            )
            collector.add_relationship_if_present(
                relationship_type="certified_by",
                source_entity_type="domain",
                source_value=domain_value,
                target_entity_type="organization",
                target_value=issuer_canonical,
                metadata={"certificate_index": certificate_index},
            )

    return collector.build()


def _extract_nominatim_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from Nominatim normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="Nominatim normalized data must be a dictionary before shared extraction.",
        )

    collector = _ArtifactCollector(normalized_record)

    if "place" in normalized_record.normalized_data:
        place = normalized_record.normalized_data.get("place")
        if not isinstance(place, dict):
            return _build_bad_normalized_data_record(
                normalized_record,
                message="Nominatim reverse normalized place must be a dictionary.",
            )

        collector.add_place_entity(
            display_name=_to_text(place.get("display_name")),
            latitude=_to_float_or_none(place.get("latitude")),
            longitude=_to_float_or_none(place.get("longitude")),
            detail="Nominatim reverse place result.",
        )
        return collector.build()

    places = normalized_record.normalized_data.get("places")
    if not isinstance(places, list):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="Nominatim search normalized data must include a places list.",
        )

    for place_index, place in enumerate(places):
        if not isinstance(place, dict):
            return _build_bad_normalized_data_record(
                normalized_record,
                message="Each Nominatim place must be a dictionary before shared extraction.",
            )

        collector.add_place_entity(
            display_name=_to_text(place.get("display_name")),
            latitude=_to_float_or_none(place.get("latitude")),
            longitude=_to_float_or_none(place.get("longitude")),
            detail="Nominatim search place result.",
            metadata={"place_index": place_index},
        )

    return collector.build()


def _extract_opensky_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from OpenSky normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="OpenSky normalized data must be a dictionary before shared extraction.",
        )

    collector = _ArtifactCollector(normalized_record)

    if "aircraft" in normalized_record.normalized_data:
        aircraft = normalized_record.normalized_data.get("aircraft")
        if aircraft is None:
            return collector.build()

        if not isinstance(aircraft, dict):
            return _build_bad_normalized_data_record(
                normalized_record,
                message="OpenSky aircraft normalized data must be a dictionary.",
            )

        _add_aircraft_bundle(collector, aircraft, metadata={"mode": "aircraft"})
        return collector.build()

    states = normalized_record.normalized_data.get("states")
    if not isinstance(states, list):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="OpenSky bounds normalized data must include a states list.",
        )

    for state_index, state in enumerate(states):
        if not isinstance(state, dict):
            return _build_bad_normalized_data_record(
                normalized_record,
                message="Each OpenSky normalized state must be a dictionary.",
            )

        _add_aircraft_bundle(collector, state, metadata={"mode": "bounds", "state_index": state_index})

    return collector.build()


def _extract_webhook_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from webhook normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="Webhook normalized data must be a dictionary before shared extraction.",
        )

    payload = normalized_record.normalized_data.get("payload")
    if not isinstance(payload, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="Webhook normalized data must include a payload dictionary.",
        )

    collector = _ArtifactCollector(normalized_record)
    _extract_generic_mapping_artifacts(
        collector=collector,
        mapping=payload,
        detail_prefix="Webhook payload",
    )
    return collector.build()


def _extract_csv_upload_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from CSV-upload normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="CSV upload normalized data must be a dictionary before shared extraction.",
        )

    rows = normalized_record.normalized_data.get("rows")
    if not isinstance(rows, list):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="CSV upload normalized data must include a rows list.",
        )

    collector = _ArtifactCollector(normalized_record)
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            return _build_bad_normalized_data_record(
                normalized_record,
                message="Each CSV upload normalized row must be a dictionary.",
            )

        _extract_generic_mapping_artifacts(
            collector=collector,
            mapping=row,
            detail_prefix=f"CSV row {row_index}",
            metadata={"row_index": row_index},
        )

    return collector.build()


def _extract_manual_input_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from manual-input normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="Manual input normalized data must be a dictionary before shared extraction.",
        )

    fields = normalized_record.normalized_data.get("fields")
    if not isinstance(fields, dict):
        return _build_bad_normalized_data_record(
            normalized_record,
            message="Manual input normalized data must include a fields dictionary.",
        )

    collector = _ArtifactCollector(normalized_record)
    _extract_generic_mapping_artifacts(
        collector=collector,
        mapping=fields,
        detail_prefix="Manual input fields",
    )
    return collector.build()


def _extract_generic_mapping_artifacts(
    *,
    collector: "_ArtifactCollector",
    mapping: dict[str, Any],
    detail_prefix: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Extract simple person/domain/IP-style artifacts from a generic mapping."""
    extra_metadata = dict(metadata or {})

    person_name = _first_text_value(mapping, "full_name", "person_name", "name")
    company_value = _first_text_value(mapping, "company_name", "company")
    organization_value = _first_text_value(mapping, "organization", "org")
    city = _first_text_value(mapping, "city")
    region = _first_text_value(mapping, "region", "state")
    country = _first_text_value(mapping, "country")
    email_values = _collect_text_values(mapping, "emails", "email")
    domain_values = _collect_text_values(mapping, "domains", "domain")
    ip_values = _collect_text_values(mapping, "ip_addresses", "ip_address", "ips", "ip")

    person_canonical = collector.add_person_entity(
        person_name,
        detail=f"{detail_prefix} person name.",
        metadata=extra_metadata,
    )
    company_canonical = collector.add_company_entity(
        company_value,
        detail=f"{detail_prefix} company value.",
        metadata=extra_metadata,
    )
    organization_canonical = collector.add_organization_entity(
        organization_value,
        detail=f"{detail_prefix} organization value.",
        metadata=extra_metadata,
    )
    place_canonical = collector.add_place_entity(
        city=city,
        region=region,
        country=country,
        detail=f"{detail_prefix} place bundle.",
        metadata=extra_metadata,
    )

    email_canonicals: list[str] = []
    for email_value in email_values:
        email_canonical = collector.add_email_entity(
            email_value,
            detail=f"{detail_prefix} email value.",
            metadata=extra_metadata,
        )
        if email_canonical:
            email_canonicals.append(email_canonical)

    domain_canonicals: list[str] = []
    for domain_value in domain_values:
        domain_canonical = collector.add_domain_entity(
            domain_value,
            detail=f"{detail_prefix} domain value.",
            metadata=extra_metadata,
        )
        if domain_canonical:
            domain_canonicals.append(domain_canonical)

    ip_canonicals: list[str] = []
    for ip_value in ip_values:
        ip_canonical = collector.add_ip_entity(
            ip_value,
            detail=f"{detail_prefix} IP value.",
            metadata=extra_metadata,
        )
        if ip_canonical:
            ip_canonicals.append(ip_canonical)

    for email_canonical in email_canonicals:
        collector.add_relationship_if_present(
            relationship_type="uses",
            source_entity_type="person",
            source_value=person_canonical,
            target_entity_type="email",
            target_value=email_canonical,
            metadata=extra_metadata,
        )

    for domain_canonical in domain_canonicals:
        collector.add_relationship_if_present(
            relationship_type="associated_with",
            source_entity_type="person",
            source_value=person_canonical,
            target_entity_type="domain",
            target_value=domain_canonical,
            metadata=extra_metadata,
        )
        collector.add_relationship_if_present(
            relationship_type="associated_with",
            source_entity_type="person",
            source_value=person_canonical,
            target_entity_type="organization",
            target_value=company_canonical,
            metadata=extra_metadata,
        )
        collector.add_relationship_if_present(
            relationship_type="associated_with",
            source_entity_type="person",
            source_value=person_canonical,
            target_entity_type="organization",
            target_value=organization_canonical,
            metadata=extra_metadata,
        )

    for ip_canonical in ip_canonicals:
        collector.add_relationship_if_present(
            relationship_type="points_to",
            source_entity_type="domain",
            source_value=domain_canonicals[0] if domain_canonicals else "",
            target_entity_type="ip",
            target_value=ip_canonical,
            metadata=extra_metadata,
        )
        collector.add_relationship_if_present(
            relationship_type="associated_with",
            source_entity_type="ip",
            source_value=ip_canonical,
            target_entity_type="organization",
            target_value=organization_canonical,
            metadata=extra_metadata,
        )
        collector.add_relationship_if_present(
            relationship_type="located_in",
            source_entity_type="ip",
            source_value=ip_canonical,
            target_entity_type="place",
            target_value=place_canonical,
            metadata=extra_metadata,
        )


def _add_aircraft_bundle(
    collector: "_ArtifactCollector",
    aircraft: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Add aircraft and optional place artifacts from one OpenSky aircraft-like dict."""
    extra_metadata = dict(metadata or {})
    icao24 = _to_text(aircraft.get("icao24"))
    callsign = _to_text(aircraft.get("callsign"))
    origin_country = _to_text(aircraft.get("origin_country"))
    longitude = _to_float_or_none(aircraft.get("longitude"))
    latitude = _to_float_or_none(aircraft.get("latitude"))

    aircraft_canonical = collector.add_aircraft_entity(
        icao24,
        callsign=callsign,
        origin_country=origin_country,
        longitude=longitude,
        latitude=latitude,
        detail="OpenSky aircraft observation.",
        metadata=extra_metadata,
    )
    place_canonical = collector.add_place_entity(
        latitude=latitude,
        longitude=longitude,
        detail="OpenSky aircraft observation coordinates.",
        metadata=extra_metadata,
    )
    collector.add_relationship_if_present(
        relationship_type="observed_over",
        source_entity_type="aircraft",
        source_value=aircraft_canonical,
        target_entity_type="place",
        target_value=place_canonical,
        metadata=extra_metadata,
    )


def _build_output_record(
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


def _build_bad_normalized_data_record(
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


class _ArtifactCollector:
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
        return _build_output_record(
            self.normalized_record,
            entities=self.entities,
            evidence=self.evidence,
            relationship_candidates=self.relationship_candidates,
        )

    def add_person_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add a person entity when the value is usable."""
        canonical_value = _canonical_person(value)
        if not canonical_value:
            return ""

        display_value = _to_text(value)
        self._add_entity("person", canonical_value, display_value, metadata=metadata)
        self._add_evidence("person", canonical_value, "person_field", detail, metadata=metadata)
        return canonical_value

    def add_email_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add an email entity when the value is usable."""
        canonical_value = _canonical_email(value)
        if not canonical_value:
            return ""

        self._add_entity("email", canonical_value, canonical_value, metadata=metadata)
        self._add_evidence("email", canonical_value, "email_field", detail, metadata=metadata)
        return canonical_value

    def add_domain_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add a domain entity when the value is usable."""
        canonical_value = _canonical_domain(value)
        if not canonical_value:
            return ""

        display_value = _to_text(value) or canonical_value
        self._add_entity("domain", canonical_value, display_value, metadata=metadata)
        self._add_evidence("domain", canonical_value, "domain_field", detail, metadata=metadata)
        return canonical_value

    def add_ip_entity(self, value: object, *, detail: str, metadata: dict[str, Any] | None = None) -> str:
        """Add an IP entity when the value is usable."""
        canonical_value = _canonical_ip(value)
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
        canonical_value = _canonical_organization(value)
        if not canonical_value:
            return ""

        display_value = _to_text(value) or canonical_value
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
        canonical_value = _canonical_organization(value)
        if not canonical_value:
            return ""

        display_value = _to_text(value) or canonical_value
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
        canonical_value = _canonical_place(
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
        canonical_value = _canonical_aircraft(value)
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

        self._add_entity("aircraft", canonical_value, _to_text(value) or canonical_value, metadata=entity_metadata)
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


def _extract_certificate_domains(certificate: dict[str, Any]) -> list[str]:
    """Return cleaned domain values from one normalized crt.sh certificate."""
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
        canonical_value = _canonical_domain(raw_value)
        if not canonical_value:
            continue

        if canonical_value in seen_domains:
            continue

        seen_domains.add(canonical_value)
        domains.append(canonical_value)

    return domains


def _collect_text_values(mapping: dict[str, Any], *keys: str) -> list[str]:
    """Collect string or string-list values from one mapping."""
    values: list[str] = []
    for key in keys:
        value = mapping.get(key)
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


def _first_text_value(mapping: dict[str, Any], *keys: str) -> str:
    """Return the first clean text value found under the given keys."""
    for key in keys:
        value = mapping.get(key)
        if not isinstance(value, str):
            continue

        stripped_value = value.strip()
        if stripped_value:
            return stripped_value

    return ""


def _canonical_domain(value: object) -> str:
    """Return a clean comparable domain value."""
    if not isinstance(value, str):
        return ""

    normalized_value = value.strip().lower()
    if normalized_value.startswith("*."):
        normalized_value = normalized_value[2:]

    if not is_valid_domain_name(normalized_value):
        return ""

    return normalized_value


def _canonical_ip(value: object) -> str:
    """Return a clean comparable IPv4 value."""
    if not isinstance(value, str):
        return ""

    normalized_value = value.strip()
    if not is_valid_ipv4_address(normalized_value):
        return ""

    return normalized_value


def _canonical_email(value: object) -> str:
    """Return a clean comparable email value."""
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


def _canonical_organization(value: object) -> str:
    """Return a clean comparable organization value."""
    return _normalize_free_text(value)


def _canonical_person(value: object) -> str:
    """Return a clean comparable person value."""
    return _normalize_free_text(value)


def _canonical_aircraft(value: object) -> str:
    """Return a clean comparable aircraft id value."""
    if not isinstance(value, str):
        return ""

    return value.strip().lower()


def _canonical_place(
    *,
    city: str = "",
    region: str = "",
    country: str = "",
    display_name: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
) -> str:
    """Return a clean comparable place value from names or coordinates."""
    display_canonical = _normalize_free_text(display_name)
    if display_canonical:
        return display_canonical

    place_parts = [city, region, country]
    cleaned_parts = [_normalize_free_text(part) for part in place_parts if _normalize_free_text(part)]
    if cleaned_parts:
        return "|".join(cleaned_parts)

    if latitude is None or longitude is None:
        return ""

    return f"{latitude:.4f},{longitude:.4f}"


def _normalize_free_text(value: object) -> str:
    """Return a simple lowercase alphanumeric comparable string."""
    if not isinstance(value, str):
        return ""

    normalized_value = value.strip().lower()
    if not normalized_value:
        return ""

    normalized_value = re.sub(r"[^a-z0-9]+", " ", normalized_value)
    normalized_value = re.sub(r"\s+", " ", normalized_value)
    return normalized_value.strip()


def _to_text(value: object) -> str:
    """Return a safe stripped text value."""
    if not isinstance(value, str):
        return ""

    return value.strip()


def _to_float_or_none(value: object) -> float | None:
    """Return a float when possible."""
    try:
        if value is None:
            return None

        return float(value)
    except (TypeError, ValueError):
        return None
