"""Small environment-based settings for the project."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


def _read_text(name: str, default: str) -> str:
    """Read one environment variable as a clean string."""
    value = os.getenv(name)
    if value is None:
        return default

    cleaned_value = value.strip()
    if not cleaned_value:
        return default

    return cleaned_value


def _read_int(name: str, default: int) -> int:
    """Read one environment variable as an integer."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    cleaned_value = raw_value.strip()
    if not cleaned_value:
        return default

    try:
        return int(cleaned_value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """A tiny bag of project settings."""

    app_name: str = "SightlineOSINT"
    app_env: str = "development"
    request_timeout_seconds: int = 30
    raw_storage_path: str = "data/raw"
    neo4j_url: str = "bolt://localhost:7687"
    ipinfo_api_key: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings once and reuse them."""
    return Settings(
        app_name=_read_text("APP_NAME", "SightlineOSINT"),
        app_env=_read_text("APP_ENV", "development"),
        request_timeout_seconds=_read_int("REQUEST_TIMEOUT_SECONDS", 30),
        raw_storage_path=_read_text("RAW_STORAGE_PATH", "data/raw"),
        neo4j_url=_read_text("NEO4J_URL", "bolt://localhost:7687"),
        ipinfo_api_key=_read_text("IPINFO_API_KEY", ""),
    )
