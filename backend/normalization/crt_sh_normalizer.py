"""Normalizer for saved crt.sh raw records."""

from __future__ import annotations

from typing import Any

from backend.normalization.common import build_bad_raw_data_record
from backend.normalization.common import build_passthrough_record
from backend.normalization.common import build_success_record
from backend.normalization.common import to_text
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord


def normalize_crt_sh_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved crt.sh raw record into the shared normalized shape."""
    if saved_raw_record.status == FetchStatus.NO_RESULTS:
        return _build_no_results_record(saved_raw_record)

    if saved_raw_record.status != FetchStatus.SUCCESS:
        return build_passthrough_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, list):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="crt.sh raw data must be a list before normalization.",
        )

    certificates: list[dict[str, Any]] = []
    for item in saved_raw_record.raw_data:
        if not isinstance(item, dict):
            return build_bad_raw_data_record(
                saved_raw_record,
                message="Each crt.sh certificate record must be a dictionary.",
            )

        normalized_certificate = {
            "common_name": to_text(item.get("common_name")),
            "issuer_name": to_text(item.get("issuer_name")),
            "not_before": to_text(item.get("not_before")),
        }

        name_value = to_text(item.get("name_value"))
        if name_value:
            normalized_certificate["name_value"] = name_value

        certificates.append(normalized_certificate)

    return build_success_record(saved_raw_record, normalized_data={"certificates": certificates})


def _build_no_results_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Normalize an empty crt.sh result into an empty certificates list."""
    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.NO_RESULTS,
        error=None,
        normalized_data={"certificates": []},
        metadata=dict(saved_raw_record.metadata),
    )
