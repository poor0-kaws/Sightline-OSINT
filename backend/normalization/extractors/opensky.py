"""Shared artifact extraction for OpenSky normalized records."""

from __future__ import annotations

from typing import Any

from backend.normalization.extractors.collector import ArtifactCollector
from backend.normalization.extractors.collector import build_bad_normalized_data_record
from backend.normalization.schemas import NormalizedRecord
from backend.utils.text import to_float_or_none
from backend.utils.text import to_text


def extract_opensky_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from OpenSky normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="OpenSky normalized data must be a dictionary before shared extraction.",
        )

    collector = ArtifactCollector(normalized_record)

    if "aircraft" in normalized_record.normalized_data:
        aircraft = normalized_record.normalized_data.get("aircraft")
        if aircraft is None:
            return collector.build()

        if not isinstance(aircraft, dict):
            return build_bad_normalized_data_record(
                normalized_record,
                message="OpenSky aircraft normalized data must be a dictionary.",
            )

        _add_aircraft_bundle(collector, aircraft, metadata={"mode": "aircraft"})
        return collector.build()

    states = normalized_record.normalized_data.get("states")
    if not isinstance(states, list):
        return build_bad_normalized_data_record(
            normalized_record,
            message="OpenSky bounds normalized data must include a states list.",
        )

    for state_index, state in enumerate(states):
        if not isinstance(state, dict):
            return build_bad_normalized_data_record(
                normalized_record,
                message="Each OpenSky normalized state must be a dictionary.",
            )

        _add_aircraft_bundle(collector, state, metadata={"mode": "bounds", "state_index": state_index})

    return collector.build()


def _add_aircraft_bundle(
    collector: ArtifactCollector,
    aircraft: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Add aircraft and optional place artifacts from one OpenSky aircraft-like dict."""
    extra_metadata = dict(metadata or {})
    icao24 = to_text(aircraft.get("icao24"))
    callsign = to_text(aircraft.get("callsign"))
    origin_country = to_text(aircraft.get("origin_country"))
    longitude = to_float_or_none(aircraft.get("longitude"))
    latitude = to_float_or_none(aircraft.get("latitude"))

    aircraft_canonical = collector.add_aircraft_entity(
        icao24,
        callsign=callsign,
        origin_country=origin_country,
        longitude=longitude,
        latitude=latitude,
        detail="OpenSky aircraft observation.",
        metadata=extra_metadata,
    )
    place_canonical = collector.add_place_entity(
        latitude=latitude,
        longitude=longitude,
        detail="OpenSky aircraft observation coordinates.",
        metadata=extra_metadata,
    )
    collector.add_relationship_if_present(
        relationship_type="observed_over",
        source_entity_type="aircraft",
        source_value=aircraft_canonical,
        target_entity_type="place",
        target_value=place_canonical,
        metadata=extra_metadata,
    )
