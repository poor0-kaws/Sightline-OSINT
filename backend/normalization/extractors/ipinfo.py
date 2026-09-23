"""Shared artifact extraction for IPinfo normalized records."""

from __future__ import annotations

from backend.normalization.extractors.collector import ArtifactCollector
from backend.normalization.extractors.collector import build_bad_normalized_data_record
from backend.normalization.extractors.collector import canonical_place
from backend.normalization.schemas import NormalizedRecord
from backend.utils.identifiers import normalize_domain
from backend.utils.identifiers import normalize_ipv4
from backend.utils.text import normalize_free_text
from backend.utils.text import to_text


def extract_ipinfo_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from IPinfo normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="IPinfo normalized data must be a dictionary before shared extraction.",
        )

    collector = ArtifactCollector(normalized_record)

    ip_value = normalized_record.normalized_data.get("ip_address")
    organization_value = normalized_record.normalized_data.get("organization")
    as_domain = normalized_record.normalized_data.get("as_domain")
    city = to_text(normalized_record.normalized_data.get("city"))
    region = to_text(normalized_record.normalized_data.get("region"))
    country = to_text(normalized_record.normalized_data.get("country"))

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
        source_value=normalize_ipv4(ip_value),
        target_entity_type="organization",
        target_value=normalize_free_text(organization_value),
    )
    collector.add_relationship_if_present(
        relationship_type="associated_with",
        source_entity_type="ip",
        source_value=normalize_ipv4(ip_value),
        target_entity_type="domain",
        target_value=normalize_domain(as_domain, strip_wildcard=True),
    )
    collector.add_relationship_if_present(
        relationship_type="located_in",
        source_entity_type="ip",
        source_value=normalize_ipv4(ip_value),
        target_entity_type="place",
        target_value=canonical_place(city=city, region=region, country=country),
    )

    return collector.build()
