"""Shared artifact extraction for generic mapping payloads.

Webhook, CSV-upload, and manual-input records all reduce to "a mapping of
fields", so they share one generic field extractor.
"""

from __future__ import annotations

from typing import Any

from backend.normalization.extractors.collector import ArtifactCollector
from backend.normalization.extractors.collector import build_bad_normalized_data_record
from backend.normalization.schemas import NormalizedRecord
from backend.utils.text import collect_text_values
from backend.utils.text import first_text_value


def extract_webhook_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from webhook normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="Webhook normalized data must be a dictionary before shared extraction.",
        )

    payload = normalized_record.normalized_data.get("payload")
    if not isinstance(payload, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="Webhook normalized data must include a payload dictionary.",
        )

    collector = ArtifactCollector(normalized_record)
    extract_generic_mapping_artifacts(
        collector=collector,
        mapping=payload,
        detail_prefix="Webhook payload",
    )
    return collector.build()


def extract_csv_upload_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from CSV-upload normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="CSV upload normalized data must be a dictionary before shared extraction.",
        )

    rows = normalized_record.normalized_data.get("rows")
    if not isinstance(rows, list):
        return build_bad_normalized_data_record(
            normalized_record,
            message="CSV upload normalized data must include a rows list.",
        )

    collector = ArtifactCollector(normalized_record)
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            return build_bad_normalized_data_record(
                normalized_record,
                message="Each CSV upload normalized row must be a dictionary.",
            )

        extract_generic_mapping_artifacts(
            collector=collector,
            mapping=row,
            detail_prefix=f"CSV row {row_index}",
            metadata={"row_index": row_index},
        )

    return collector.build()


def extract_manual_input_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from manual-input normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="Manual input normalized data must be a dictionary before shared extraction.",
        )

    fields = normalized_record.normalized_data.get("fields")
    if not isinstance(fields, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="Manual input normalized data must include a fields dictionary.",
        )

    collector = ArtifactCollector(normalized_record)
    extract_generic_mapping_artifacts(
        collector=collector,
        mapping=fields,
        detail_prefix="Manual input fields",
    )
    return collector.build()


def extract_generic_mapping_artifacts(
    *,
    collector: ArtifactCollector,
    mapping: dict[str, Any],
    detail_prefix: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Extract simple person/domain/IP-style artifacts from a generic mapping."""
    extra_metadata = dict(metadata or {})

    person_name = first_text_value(mapping, "full_name", "person_name", "name")
    company_value = first_text_value(mapping, "company_name", "company")
    organization_value = first_text_value(mapping, "organization", "org")
    city = first_text_value(mapping, "city")
    region = first_text_value(mapping, "region", "state")
    country = first_text_value(mapping, "country")
    email_values = collect_text_values(mapping, "emails", "email")
    domain_values = collect_text_values(mapping, "domains", "domain")
    ip_values = collect_text_values(mapping, "ip_addresses", "ip_address", "ips", "ip")

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
