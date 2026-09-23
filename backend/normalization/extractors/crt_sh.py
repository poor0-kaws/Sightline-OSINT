"""Shared artifact extraction for crt.sh normalized records."""

from __future__ import annotations

from backend.normalization.extractors.collector import ArtifactCollector
from backend.normalization.extractors.collector import build_bad_normalized_data_record
from backend.normalization.extractors.collector import extract_certificate_domains
from backend.normalization.schemas import NormalizedRecord
from backend.utils.text import normalize_free_text


def extract_crt_sh_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from crt.sh normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="crt.sh normalized data must be a dictionary before shared extraction.",
        )

    certificates = normalized_record.normalized_data.get("certificates")
    if not isinstance(certificates, list):
        return build_bad_normalized_data_record(
            normalized_record,
            message="crt.sh normalized data must include a certificates list before shared extraction.",
        )

    collector = ArtifactCollector(normalized_record)

    for certificate_index, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            return build_bad_normalized_data_record(
                normalized_record,
                message="Each crt.sh certificate must be a dictionary before shared extraction.",
            )

        issuer_name = certificate.get("issuer_name")
        issuer_canonical = normalize_free_text(issuer_name)
        collector.add_organization_entity(
            issuer_name,
            detail="crt.sh certificate issuer.",
            metadata={"certificate_index": certificate_index},
        )

        for domain_value in extract_certificate_domains(certificate):
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
