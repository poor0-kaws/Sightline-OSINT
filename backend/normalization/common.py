"""Shared helpers for provider-specific normalizers."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.storage import SavedRawRecord


def build_success_record(
    saved_raw_record: SavedRawRecord,
    *,
    normalized_data: Any,
) -> NormalizedRecord:
    """Return one success-shaped normalized record."""
    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        case_id=saved_raw_record.case_id,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.SUCCESS,
        error=None,
        normalized_data=normalized_data,
        metadata=dict(saved_raw_record.metadata),
    )


def build_passthrough_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Keep already-failed raw records in the same error shape."""
    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        case_id=saved_raw_record.case_id,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=saved_raw_record.status,
        error=saved_raw_record.error,
        normalized_data=None,
        metadata=dict(saved_raw_record.metadata),
    )


def build_bad_raw_data_record(
    saved_raw_record: SavedRawRecord,
    *,
    message: str,
) -> NormalizedRecord:
    """Return a clean normalization error for malformed raw data."""
    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        case_id=saved_raw_record.case_id,
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
