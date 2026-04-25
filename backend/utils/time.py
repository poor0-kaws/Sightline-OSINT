"""Small time helpers."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone


def utc_now_iso() -> str:
    """Return the current time in UTC as an ISO string."""
    return datetime.now(timezone.utc).isoformat()
