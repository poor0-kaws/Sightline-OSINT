"""Normalizer for saved manual-input raw records."""

from __future__ import annotations

from backend.normalization.common import build_bad_raw_data_record
from backend.normalization.common import build_passthrough_record
from backend.normalization.common import build_success_record
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord


def normalize_manual_input_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved manual-input raw record into the shared normalized shape."""
    if saved_raw_record.status != FetchStatus.SUCCESS:
        return build_passthrough_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, dict):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="Manual input raw data must be a dictionary before normalization.",
        )

    return build_success_record(saved_raw_record, normalized_data={"fields": saved_raw_record.raw_data})
