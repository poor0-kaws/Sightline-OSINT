"""Normalizer for saved crt.sh raw records."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.storage import SavedRawRecord


def normalize_crt_sh_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved crt.sh raw record into the shared normalized shape."""
    if saved_raw_record.status == FetchStatus.NO_RESULTS:
        return _build_no_results_record(saved_raw_record)

    if saved_raw_record.status != FetchStatus.SUCCESS:
        return _build_passthrough_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, list):
        return _build_bad_raw_data_record(
            saved_raw_record,
            message="crt.sh raw data must be a list before normalization.",
        )

    certificates: list[dict[str, Any]] = []
    for item in saved_raw_record.raw_data:
        if not isinstance(item, dict):
            return _build_bad_raw_data_record(
                saved_raw_record,
                message="Each crt.sh certificate record must be a dictionary.",
            )

        normalized_certificate = {
            "common_name": _to_text(item.get("common_name")),
            "issuer_name": _to_text(item.get("issuer_name")),
            "not_before": _to_text(item.get("not_before")),
        }

        name_value = _to_text(item.get("name_value"))
        if name_value:
            normalized_certificate["name_value"] = name_value

        certificates.append(normalized_certificate)

    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.SUCCESS,
        error=None,
        normalized_data={"certificates": certificates},
        metadata=dict(saved_raw_record.metadata),
    )


def _build_passthrough_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Keep provider failures in the same error shape after normalization."""
    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=saved_raw_record.status,
        error=saved_raw_record.error,
        normalized_data=None,
        metadata=dict(saved_raw_record.metadata),
    )


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


def _build_bad_raw_data_record(
    saved_raw_record: SavedRawRecord,
    *,
    message: str,
) -> NormalizedRecord:
    """Return a clean normalization error when crt.sh raw data is malformed."""
    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.ERROR,
        error=ProviderError(
            code=ErrorCode.NORMALIZATION_BAD_RAW_DATA.value,
            message=message,
        ),
        normalized_data=None,
        metadata=dict(saved_raw_record.metadata),
    )


def _to_text(value: object) -> str:
    """Turn a maybe-string field into a clean string."""
    if value is None:
        return ""

    return str(value).strip()
