"""Normalizer for saved IPinfo raw records."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.storage import SavedRawRecord


def normalize_ipinfo_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved IPinfo raw record into the shared normalized shape."""
    if saved_raw_record.status != FetchStatus.SUCCESS:
        return _build_passthrough_error_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, dict):
        return _build_bad_raw_data_record(
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

    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.SUCCESS,
        error=None,
        normalized_data=normalized_data,
        metadata=dict(saved_raw_record.metadata),
    )


def _build_passthrough_error_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Return an error-shaped normalized record when the raw fetch already failed."""
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


def _build_bad_raw_data_record(
    saved_raw_record: SavedRawRecord,
    *,
    message: str,
) -> NormalizedRecord:
    """Return an error-shaped normalized record for malformed raw data."""
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
