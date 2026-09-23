"""Shared identifier canonicalization used across the domain layers.

These helpers normalize values that are compared for exact equality (IP
addresses, domain names, email addresses). Layer-specific policy — role-based or
placeholder email filters, phone rules — stays in the layer that owns it.
"""

from __future__ import annotations

from backend.utils.validation import is_valid_domain_name
from backend.utils.validation import is_valid_ipv4_address


def normalize_ipv4(value: object) -> str:
    """Return a clean comparable IPv4 address, or an empty string."""
    if not isinstance(value, str):
        return ""

    candidate = value.strip()
    if not candidate:
        return ""

    if not is_valid_ipv4_address(candidate):
        return ""

    return candidate


def normalize_domain(value: object, *, strip_wildcard: bool = False) -> str:
    """Return a clean comparable domain name, or an empty string."""
    if not isinstance(value, str):
        return ""

    candidate = value.strip().lower()
    if not candidate:
        return ""

    if strip_wildcard and candidate.startswith("*."):
        candidate = candidate[2:]

    if not is_valid_domain_name(candidate):
        return ""

    return candidate


def normalize_email(value: object) -> str:
    """Return a clean comparable email address, or an empty string."""
    if not isinstance(value, str):
        return ""

    candidate = value.strip().lower()
    if not candidate or "@" not in candidate:
        return ""

    local_part, separator, domain_part = candidate.partition("@")
    if not separator or not local_part or not domain_part:
        return ""

    if "." not in domain_part:
        return ""

    return f"{local_part}@{domain_part}"
