"""Small helpers for turning messy values into safe values."""

from __future__ import annotations


def clean_text(value: object) -> str:
    """Turn a maybe-missing value into a stripped string."""
    if value is None:
        return ""

    return str(value).strip()


def clean_int(value: object, default: int = 30) -> int:
    """Turn a maybe-missing value into an integer."""
    if value is None:
        return default

    if isinstance(value, bool):
        return default

    if isinstance(value, int):
        return value

    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default
