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
    max_request_bytes: int = 1_000_000
    rate_limit_per_minute: int = 120
    raw_storage_path: str = "data/raw"
    audit_log_path: str = "data/audit.log"
    api_auth_token: str = ""
    graph_repository_kind: str = "memory"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_username: str = ""
    neo4j_password: str = ""
    ipinfo_api_key: str = ""


@lru_cache(maxsize=32)
def _build_cached_settings(
    app_name: str,
    app_env: str,
    request_timeout_seconds: int,
    max_request_bytes: int,
    rate_limit_per_minute: int,
    raw_storage_path: str,
    audit_log_path: str,
    api_auth_token: str,
    graph_repository_kind: str,
    neo4j_url: str,
    neo4j_username: str,
    neo4j_password: str,
    ipinfo_api_key: str,
) -> Settings:
    """Reuse settings objects for the same environment values."""
    return Settings(
        app_name=app_name,
        app_env=app_env,
        request_timeout_seconds=request_timeout_seconds,
        max_request_bytes=max_request_bytes,
        rate_limit_per_minute=rate_limit_per_minute,
        raw_storage_path=raw_storage_path,
        audit_log_path=audit_log_path,
        api_auth_token=api_auth_token,
        graph_repository_kind=graph_repository_kind,
        neo4j_url=neo4j_url,
        neo4j_username=neo4j_username,
        neo4j_password=neo4j_password,
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

    if settings.max_request_bytes <= 0:
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: MAX_REQUEST_BYTES must be greater than zero.")

    if settings.rate_limit_per_minute <= 0:
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: RATE_LIMIT_PER_MINUTE must be greater than zero.")

    if not settings.raw_storage_path.strip():
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: RAW_STORAGE_PATH is required.")

    if not settings.audit_log_path.strip():
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: AUDIT_LOG_PATH is required.")

    if settings.graph_repository_kind not in {"memory", "neo4j"}:
        raise ValueError(
            f"{ErrorCode.INVALID_SETTINGS.value}: GRAPH_REPOSITORY_KIND must be memory or neo4j."
        )

    if not settings.neo4j_url.strip():
        raise ValueError(f"{ErrorCode.INVALID_SETTINGS.value}: NEO4J_URL is required.")

    return settings


def get_settings() -> Settings:
    """Build settings once and reuse them."""
    return _build_cached_settings(
        app_name=_read_text("APP_NAME", "SightlineOSINT"),
        app_env=_read_text("APP_ENV", "development"),
        request_timeout_seconds=_read_int("REQUEST_TIMEOUT_SECONDS", 30),
        max_request_bytes=_read_int("MAX_REQUEST_BYTES", 1_000_000),
        rate_limit_per_minute=_read_int("RATE_LIMIT_PER_MINUTE", 120),
        raw_storage_path=_read_text("RAW_STORAGE_PATH", "data/raw"),
        audit_log_path=_read_text("AUDIT_LOG_PATH", "data/audit.log"),
        api_auth_token=_read_text("API_AUTH_TOKEN", ""),
        graph_repository_kind=_read_text("GRAPH_REPOSITORY_KIND", "memory").lower(),
        neo4j_url=_read_text("NEO4J_URL", "bolt://localhost:7687"),
        neo4j_username=_read_text("NEO4J_USERNAME", ""),
        neo4j_password=_read_text("NEO4J_PASSWORD", ""),
        ipinfo_api_key=_read_text("IPINFO_API_KEY", ""),
    )


def get_validated_settings() -> Settings:
    """Build settings and validate them for startup use."""
    return validate_settings(get_settings())


get_settings.cache_clear = _build_cached_settings.cache_clear
