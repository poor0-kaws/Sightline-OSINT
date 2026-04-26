"""Normalizer for saved Nominatim raw records."""

from __future__ import annotations

from typing import Any

from backend.normalization.common import build_bad_raw_data_record
from backend.normalization.common import build_passthrough_record
from backend.normalization.common import build_success_record
from backend.normalization.common import to_float_or_none
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord


def normalize_nominatim_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved Nominatim raw record into the shared normalized shape."""
    if saved_raw_record.status != FetchStatus.SUCCESS:
        return build_passthrough_record(saved_raw_record)

    mode = str(saved_raw_record.metadata.get("mode", "")).strip().lower()
    if mode == "reverse":
        return _normalize_reverse_record(saved_raw_record)

    return _normalize_search_record(saved_raw_record)


def _normalize_reverse_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Normalize one reverse-geocode raw record."""
    if not isinstance(saved_raw_record.raw_data, dict):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="Nominatim reverse raw data must be a dictionary before normalization.",
        )

    normalized_data = {
        "place": {
            "display_name": saved_raw_record.raw_data.get("display_name"),
            "latitude": to_float_or_none(saved_raw_record.raw_data.get("lat")),
            "longitude": to_float_or_none(saved_raw_record.raw_data.get("lon")),
        }
    }

    return build_success_record(saved_raw_record, normalized_data=normalized_data)


def _normalize_search_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Normalize one forward-geocode raw record."""
    if not isinstance(saved_raw_record.raw_data, list):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="Nominatim search raw data must be a list before normalization.",
        )

    places: list[dict[str, Any]] = []
    for item in saved_raw_record.raw_data:
        if not isinstance(item, dict):
            return build_bad_raw_data_record(
                saved_raw_record,
                message="Each Nominatim search result must be a dictionary.",
            )

        places.append(
            {
                "display_name": item.get("display_name"),
                "latitude": to_float_or_none(item.get("lat")),
                "longitude": to_float_or_none(item.get("lon")),
            }
        )

    normalized_data = {"places": places}

    return build_success_record(saved_raw_record, normalized_data=normalized_data)
