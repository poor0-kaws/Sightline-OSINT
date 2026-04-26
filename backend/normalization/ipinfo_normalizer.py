"""Normalizer for saved IPinfo raw records."""

from __future__ import annotations

from backend.normalization.common import build_bad_raw_data_record
from backend.normalization.common import build_passthrough_record
from backend.normalization.common import build_success_record
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord


def normalize_ipinfo_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved IPinfo raw record into the shared normalized shape."""
    if saved_raw_record.status != FetchStatus.SUCCESS:
        return build_passthrough_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, dict):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="IPinfo raw data must be a dictionary before normalization.",
        )

    normalized_data = {
        "ip_address": saved_raw_record.raw_data.get("ip"),
        "organization": saved_raw_record.raw_data.get("org"),
        "city": saved_raw_record.raw_data.get("city"),
        "region": saved_raw_record.raw_data.get("region"),
        "country": saved_raw_record.raw_data.get("country"),
    }

    return build_success_record(saved_raw_record, normalized_data=normalized_data)
