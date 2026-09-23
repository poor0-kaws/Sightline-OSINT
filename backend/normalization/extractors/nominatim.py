"""Shared artifact extraction for Nominatim normalized records."""

from __future__ import annotations

from backend.normalization.extractors.collector import ArtifactCollector
from backend.normalization.extractors.collector import build_bad_normalized_data_record
from backend.normalization.schemas import NormalizedRecord
from backend.utils.text import to_float_or_none
from backend.utils.text import to_text


def extract_nominatim_artifacts(normalized_record: NormalizedRecord) -> NormalizedRecord:
    """Extract shared artifacts from Nominatim normalized output."""
    if not isinstance(normalized_record.normalized_data, dict):
        return build_bad_normalized_data_record(
            normalized_record,
            message="Nominatim normalized data must be a dictionary before shared extraction.",
        )

    collector = ArtifactCollector(normalized_record)

    if "place" in normalized_record.normalized_data:
        place = normalized_record.normalized_data.get("place")
        if not isinstance(place, dict):
            return build_bad_normalized_data_record(
                normalized_record,
                message="Nominatim reverse normalized place must be a dictionary.",
            )

        collector.add_place_entity(
            display_name=to_text(place.get("display_name")),
            latitude=to_float_or_none(place.get("latitude")),
            longitude=to_float_or_none(place.get("longitude")),
            detail="Nominatim reverse place result.",
        )
        return collector.build()

    places = normalized_record.normalized_data.get("places")
    if not isinstance(places, list):
        return build_bad_normalized_data_record(
            normalized_record,
            message="Nominatim search normalized data must include a places list.",
        )

    for place_index, place in enumerate(places):
        if not isinstance(place, dict):
            return build_bad_normalized_data_record(
                normalized_record,
                message="Each Nominatim place must be a dictionary before shared extraction.",
            )

        collector.add_place_entity(
            display_name=to_text(place.get("display_name")),
            latitude=to_float_or_none(place.get("latitude")),
            longitude=to_float_or_none(place.get("longitude")),
            detail="Nominatim search place result.",
            metadata={"place_index": place_index},
        )

    return collector.build()
