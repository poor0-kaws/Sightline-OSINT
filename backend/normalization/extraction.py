"""Second-layer extraction of shared entities, evidence, and relationship candidates.

This module is the public entry point. The provider-specific work lives in the
``backend.normalization.extractors`` package.
"""

from __future__ import annotations

from backend.normalization.extractors import SHARED_EXTRACTOR_BY_PROVIDER
from backend.normalization.extractors.collector import build_output_record
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus


def extract_shared_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Add shared entities, evidence, and relationship candidates to one normalized record."""
    if normalized_record.status != FetchStatus.SUCCESS:
        return build_output_record(normalized_record)

    extractor = SHARED_EXTRACTOR_BY_PROVIDER.get(normalized_record.provider)
    if extractor is None:
        return build_output_record(normalized_record)

    return extractor(normalized_record)
