"""Shared helpers for turning messy values into clean comparable values.

These helpers are the single implementation for the text and identifier
canonicalization that the normalization, resolution, and relationship layers all
need. Layer-specific policies (for example a strict versus lenient phone rule)
stay in the layer that owns them.
"""

from __future__ import annotations

import re
from typing import Any

NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9]+")
WHITESPACE_PATTERN = re.compile(r"\s+")


def to_text(value: object) -> str:
    """Return a stripped string, or an empty string for non-strings."""
    if not isinstance(value, str):
        return ""

    return value.strip()


def to_string(value: object) -> str:
    """Turn any value into a stripped string, treating None as empty."""
    if value is None:
        return ""

    return str(value).strip()


def to_float_or_none(value: object) -> float | None:
    """Return a float when possible, otherwise None."""
    try:
        if value is None:
            return None

        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_free_text(value: object) -> str:
    """Lowercase and collapse punctuation and spacing into one comparable key."""
    text = to_text(value).lower()
    if not text:
        return ""

    text = NON_ALPHANUMERIC_PATTERN.sub(" ", text)
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def slugify(value: object) -> str:
    """Turn a readable value into a stable id-safe fragment."""
    text = to_text(value).lower()
    if not text:
        return "unknown"

    slug = NON_ALPHANUMERIC_PATTERN.sub("-", text).strip("-")
    if not slug:
        return "unknown"

    return slug


def first_text_value(mapping: dict[str, Any], *keys: str) -> str:
    """Return the first clean string found under the given keys."""
    for key in keys:
        value = mapping.get(key)
        if not isinstance(value, str):
            continue

        cleaned_value = value.strip()
        if cleaned_value:
            return cleaned_value

    return ""


def collect_text_values(mapping: dict[str, Any], *keys: str) -> list[str]:
    """Collect string or string-list values from one mapping."""
    values: list[str] = []
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            cleaned_value = value.strip()
            if cleaned_value:
                values.append(cleaned_value)
            continue

        if not isinstance(value, list):
            continue

        for item in value:
            if not isinstance(item, str):
                continue

            cleaned_item = item.strip()
            if cleaned_item:
                values.append(cleaned_item)

    return values
