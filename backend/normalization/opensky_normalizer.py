"""Normalizer for saved OpenSky raw records."""

from __future__ import annotations

from typing import Any

from backend.normalization.schemas import NormalizedRecord
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.storage import SavedRawRecord


def normalize_opensky_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved OpenSky raw record into the shared normalized shape."""
    if saved_raw_record.status == FetchStatus.NO_RESULTS:
        return _build_no_results_record(saved_raw_record)

    if saved_raw_record.status != FetchStatus.SUCCESS:
        return _build_passthrough_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, dict):
        return _build_bad_raw_data_record(
            saved_raw_record,
            message="OpenSky raw data must be a dictionary before normalization.",
        )

    states = saved_raw_record.raw_data.get("states")
    if not isinstance(states, list):
        return _build_bad_raw_data_record(
            saved_raw_record,
            message="OpenSky raw data must include a list states field before normalization.",
        )

    mode = str(saved_raw_record.metadata.get("mode", "")).strip().lower()
    if mode == "bounds":
        return _normalize_bounds_record(saved_raw_record=saved_raw_record, states=states)

    return _normalize_aircraft_record(saved_raw_record=saved_raw_record, states=states)


def _normalize_aircraft_record(
    *,
    saved_raw_record: SavedRawRecord,
    states: list[Any],
) -> NormalizedRecord:
    """Normalize one aircraft-style OpenSky result."""
    if not states:
        return _build_no_results_record(saved_raw_record)

    normalized_states = _normalize_state_vectors(saved_raw_record=saved_raw_record, states=states)
    if normalized_states is None:
        return _build_bad_raw_data_record(
            saved_raw_record,
            message="Each OpenSky state vector must be a list with at least 8 fields.",
        )

    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.SUCCESS,
        error=None,
        normalized_data={"aircraft": normalized_states[0]},
        metadata=dict(saved_raw_record.metadata),
    )


def _normalize_bounds_record(
    *,
    saved_raw_record: SavedRawRecord,
    states: list[Any],
) -> NormalizedRecord:
    """Normalize one bounding-box OpenSky result."""
    normalized_states = _normalize_state_vectors(saved_raw_record=saved_raw_record, states=states)
    if normalized_states is None:
        return _build_bad_raw_data_record(
            saved_raw_record,
            message="Each OpenSky state vector must be a list with at least 8 fields.",
        )

    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.SUCCESS,
        error=None,
        normalized_data={
            "states": normalized_states,
            "bounds": dict(saved_raw_record.query) if isinstance(saved_raw_record.query, dict) else None,
        },
        metadata=dict(saved_raw_record.metadata),
    )


def _normalize_state_vectors(
    *,
    saved_raw_record: SavedRawRecord,
    states: list[Any],
) -> list[dict[str, Any]] | None:
    """Turn raw OpenSky state vectors into small readable dictionaries."""
    normalized_states: list[dict[str, Any]] = []
    for state_vector in states:
        if not isinstance(state_vector, list):
            return None

        if len(state_vector) < 8:
            return None

        normalized_states.append(
            {
                "icao24": _to_text(state_vector[0]),
                "callsign": _to_text(state_vector[1]),
                "origin_country": _to_text(state_vector[2]),
                "longitude": _to_float_or_none(state_vector[5]),
                "latitude": _to_float_or_none(state_vector[6]),
                "baro_altitude": _to_float_or_none(state_vector[7]),
            }
        )

    return normalized_states


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
    """Normalize an empty OpenSky result into an empty shared payload."""
    mode = str(saved_raw_record.metadata.get("mode", "")).strip().lower()
    normalized_data: dict[str, Any]
    if mode == "bounds":
        normalized_data = {
            "states": [],
            "bounds": dict(saved_raw_record.query) if isinstance(saved_raw_record.query, dict) else None,
        }
    else:
        normalized_data = {"aircraft": None}

    return NormalizedRecord(
        provider=saved_raw_record.provider,
        source_type=saved_raw_record.source_type,
        raw_record_id=saved_raw_record.record_id,
        query=saved_raw_record.query,
        status=FetchStatus.NO_RESULTS,
        error=None,
        normalized_data=normalized_data,
        metadata=dict(saved_raw_record.metadata),
    )


def _build_bad_raw_data_record(
    saved_raw_record: SavedRawRecord,
    *,
    message: str,
) -> NormalizedRecord:
    """Return a clean normalization error when OpenSky raw data is malformed."""
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


def _to_float_or_none(value: object) -> float | None:
    """Turn a maybe-number field into a float when possible."""
    try:
        if value is None:
            return None

        return float(value)
    except (TypeError, ValueError):
        return None
