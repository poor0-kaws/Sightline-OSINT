"""Shared validation helpers for provider inputs."""

from __future__ import annotations

import ipaddress
import math
import re
from typing import Any


DOMAIN_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")
AIRCRAFT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{2,16}$")
PLACE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 .,'/-]{2,120}$")


def is_valid_ipv4_address(value: Any) -> bool:
    """Return True when the value is a valid IPv4 address."""
    if not isinstance(value, str):
        return False

    candidate = value.strip()
    if not candidate:
        return False

    try:
        parsed_ip = ipaddress.ip_address(candidate)
    except ValueError:
        return False

    return parsed_ip.version == 4


def is_valid_domain_name(value: Any) -> bool:
    """Return True when the value is a simple valid domain name."""
    if not isinstance(value, str):
        return False

    candidate = value.strip().lower()
    if not candidate:
        return False

    if "/" in candidate or ":" in candidate or "@" in candidate:
        return False

    if len(candidate) > 253:
        return False

    if "." not in candidate:
        return False

    if is_valid_ipv4_address(candidate):
        return False

    labels = candidate.split(".")
    for label in labels:
        if not label:
            return False

        if len(label) > 63:
            return False

        if label.startswith("-") or label.endswith("-"):
            return False

        if DOMAIN_LABEL_PATTERN.fullmatch(label) is None:
            return False

    top_level_label = labels[-1]
    if len(top_level_label) < 2:
        return False

    if not top_level_label.isalpha():
        return False

    return True


def get_crt_sh_query_error(value: Any) -> str | None:
    """Return a readable CRT.sh query error, or None when the query is valid."""
    if not isinstance(value, str):
        return "crt.sh expects a plain domain string like example.com."

    candidate = value.strip()
    if not candidate:
        return "crt.sh expects a plain domain string like example.com."

    if "://" in candidate:
        return "crt.sh expects a domain like example.com, not a full URL."

    if is_valid_ipv4_address(candidate):
        return "crt.sh expects a domain like example.com, not an IP address."

    if not is_valid_domain_name(candidate):
        return "crt.sh expects a domain like example.com."

    return None


def is_valid_aircraft_id(value: Any) -> bool:
    """Return True when the value looks like a usable aircraft id or callsign."""
    if not isinstance(value, str):
        return False

    if _has_control_characters(value):
        return False

    candidate = value.strip()
    if not candidate:
        return False

    return AIRCRAFT_ID_PATTERN.fullmatch(candidate) is not None


def is_valid_place_name(value: Any) -> bool:
    """Return True when the value looks like a simple place name query."""
    if not isinstance(value, str):
        return False

    candidate = value.strip()
    if not candidate:
        return False

    if _has_control_characters(candidate):
        return False

    if "://" in candidate:
        return False

    return PLACE_NAME_PATTERN.fullmatch(candidate) is not None


def has_valid_coordinates(value: Any) -> bool:
    """Return True when the value has usable lat and lon fields."""
    if not isinstance(value, dict):
        return False

    lat = _to_float(value.get("lat"))
    lon = _to_float(value.get("lon"))

    if lat is None or lon is None:
        return False

    if lat < -90 or lat > 90:
        return False

    if lon < -180 or lon > 180:
        return False

    return True


def has_valid_bounding_box(value: Any) -> bool:
    """Return True when the value has a valid map bounding box."""
    if not isinstance(value, dict):
        return False

    lamin = _to_float(value.get("lamin"))
    lamax = _to_float(value.get("lamax"))
    lomin = _to_float(value.get("lomin"))
    lomax = _to_float(value.get("lomax"))

    if lamin is None or lamax is None or lomin is None or lomax is None:
        return False

    if lamin < -90 or lamin > 90:
        return False

    if lamax < -90 or lamax > 90:
        return False

    if lomin < -180 or lomin > 180:
        return False

    if lomax < -180 or lomax > 180:
        return False

    if lamin > lamax:
        return False

    if lomin > lomax:
        return False

    if lamin == lamax:
        return False

    if lomin == lomax:
        return False

    return True


def _to_float(value: Any) -> float | None:
    """Try to turn a value into a float."""
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        parsed_value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(parsed_value):
        return None

    return parsed_value


def _has_control_characters(value: str) -> bool:
    """Return True when the string contains control characters."""
    return any(ord(character) < 32 for character in value)
