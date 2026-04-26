"""Normalizer for saved webhook raw records."""

from __future__ import annotations

from backend.normalization.common import build_bad_raw_data_record
from backend.normalization.common import build_passthrough_record
from backend.normalization.common import build_success_record
from backend.normalization.common import to_text
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord


def normalize_webhook_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved webhook raw record into the shared normalized shape."""
    if saved_raw_record.status != FetchStatus.SUCCESS:
        return build_passthrough_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, dict):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="Webhook raw data must be a dictionary before normalization.",
        )

    if "payload" not in saved_raw_record.raw_data:
        return build_bad_raw_data_record(
            saved_raw_record,
            message="Webhook raw data must include a payload field before normalization.",
        )

    payload = saved_raw_record.raw_data.get("payload")
    if not isinstance(payload, dict):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="Webhook payload must be a dictionary before normalization.",
        )

    normalized_data = {
        "event_type": to_text(saved_raw_record.raw_data.get("event_type")),
        "payload": payload,
    }
    return build_success_record(saved_raw_record, normalized_data=normalized_data)
