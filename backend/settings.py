"""Small environment-based settings for the project."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

from backend.schemas.error_codes import ErrorCode


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


@lru_cache(maxsize=32)
def _build_cached_settings(
    app_name: str,
    app_env: str,
    request_timeout_seconds: int,
    raw_storage_path: str,
    neo4j_url: str,
    ipinfo_api_key: str,
) -> Settings:
    """Reuse settings objects for the same environment values."""
    return Settings(
        app_name=app_name,
        app_env=app_env,
        request_timeout_seconds=request_timeout_seconds,
        raw_storage_path=raw_storage_path,
        neo4j_url=neo4j_url,
        ipinfo_api_key=ipinfo_api_key,
    )


def validate_settings(settings: Settings) -> Settings:
    """Reject clearly invalid startup settings."""
    if not settings.app_name.strip():
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: APP_NAME is required.")

    if not settings.app_env.strip():
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: APP_ENV is required.")

    if settings.request_timeout_seconds <= 0:
        raise ValueError(
            f"{ErrorCode.INVALID_SETTINGS.value}: REQUEST_TIMEOUT_SECONDS must be greater than zero."
        )

    if not settings.raw_storage_path.strip():
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: RAW_STORAGE_PATH is required.")

    if not settings.neo4j_url.strip():
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: NEO4J_URL is required.")

    return settings


def get_settings() -> Settings:
    """Build settings once and reuse them."""
    return _build_cached_settings(
        app_name=_read_text("APP_NAME", "SightlineOSINT"),
        app_env=_read_text("APP_ENV", "development"),
        request_timeout_seconds=_read_int("REQUEST_TIMEOUT_SECONDS", 30),
        raw_storage_path=_read_text("RAW_STORAGE_PATH", "data/raw"),
        neo4j_url=_read_text("NEO4J_URL", "bolt://localhost:7687"),
        ipinfo_api_key=_read_text("IPINFO_API_KEY", ""),
    )


def get_validated_settings() -> Settings:
    """Build settings and validate them for startup use."""
    return validate_settings(get_settings())


get_settings.cache_clear = _build_cached_settings.cache_clear
