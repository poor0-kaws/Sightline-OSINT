"""Normalizer for saved IPinfo raw records."""

from __future__ import annotations

from typing import Any

from backend.normalization.common import build_bad_raw_data_record
from backend.normalization.common import build_passthrough_record
from backend.normalization.common import build_success_record
from backend.normalization.schemas import NormalizedRecord
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord


def normalize_ipinfo_record(saved_raw_record: SavedRawRecord) -> NormalizedRecord:
    """Convert one saved IPinfo raw record into the shared normalized shape."""
    if saved_raw_record.status != FetchStatus.SUCCESS:
        return build_passthrough_record(saved_raw_record)

    if not isinstance(saved_raw_record.raw_data, dict):
        return build_bad_raw_data_record(
            saved_raw_record,
            message="IPinfo raw data must be a dictionary before normalization.",
        )

    raw_data = saved_raw_record.raw_data
    normalized_data = {
        "ip_address": raw_data.get("ip"),
        "organization": _build_organization_value(raw_data),
        "city": raw_data.get("city"),
        "region": raw_data.get("region"),
        "country": raw_data.get("country") or raw_data.get("country_code"),
        "asn": _clean_text(raw_data.get("asn")),
        "as_name": _clean_text(raw_data.get("as_name")),
        "as_domain": _clean_text(raw_data.get("as_domain")),
        "country_code": _clean_text(raw_data.get("country_code")),
        "continent": _clean_text(raw_data.get("continent")),
        "continent_code": _clean_text(raw_data.get("continent_code")),
    }

    return build_success_record(saved_raw_record, normalized_data=normalized_data)


def _build_organization_value(raw_data: dict[str, Any]) -> str:
    """Return an organization value from classic or Lite IPinfo fields."""
    classic_org = _clean_text(raw_data.get("org"))
    if classic_org:
        return classic_org

    asn = _clean_text(raw_data.get("asn"))
    as_name = _clean_text(raw_data.get("as_name"))
    if asn and as_name:
        return f"{asn} {as_name}"

    return as_name or asn


def _clean_text(value: object) -> str:
    """Return a safe string from provider data."""
    if not isinstance(value, str):
        return ""

    return value.strip()
