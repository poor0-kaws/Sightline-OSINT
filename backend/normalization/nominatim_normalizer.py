"""Normalizer for saved Nominatim raw records."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.storage import SavedRawRecord


def normalize_nominatim_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved Nominatim raw record into the shared normalized shape."""
    if saved_raw_record.status != FetchStatus.SUCCESS:
        return _build_passthrough_error_record(saved_raw_record)

    mode = str(saved_raw_record.metadata.get("mode", "")).strip().lower()
    if mode == "reverse":
        return _normalize_reverse_record(saved_raw_record)

    return _normalize_search_record(saved_raw_record)


def _normalize_reverse_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Normalize one reverse-geocode raw record."""
    if not isinstance(saved_raw_record.raw_data, dict):
        return _build_bad_raw_data_record(
            saved_raw_record,
            message="Nominatim reverse raw data must be a dictionary before normalization.",
        )

    normalized_data = {
        "place": {
            "display_name": saved_raw_record.raw_data.get("display_name"),
            "latitude": _to_float_or_none(saved_raw_record.raw_data.get("lat")),
            "longitude": _to_float_or_none(saved_raw_record.raw_data.get("lon")),
        }
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


def _normalize_search_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Normalize one forward-geocode raw record."""
    if not isinstance(saved_raw_record.raw_data, list):
        return _build_bad_raw_data_record(
            saved_raw_record,
            message="Nominatim search raw data must be a list before normalization.",
        )

    places: list[dict[str, Any]] = []
    for item in saved_raw_record.raw_data:
        if not isinstance(item, dict):
            continue

        places.append(
            {
                "display_name": item.get("display_name"),
                "latitude": _to_float_or_none(item.get("lat")),
                "longitude": _to_float_or_none(item.get("lon")),
            }
        )

    normalized_data = {"places": places}

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


def _to_float_or_none(value: object) -> float | None:
    """Convert coordinate-like values into floats when possible."""
    try:
        if value is None:
            return None

        return float(value)
    except (TypeError, ValueError):
        return None
