"""Small environment-based settings for the project."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from backend.schemas.error_codes import ErrorCode


def _read_text(name: str, default: str) -> str:
    """Read one setting as a clean string."""
    value = _read_raw_setting(name)
    if value is None:
        return default

    cleaned_value = value.strip()
    if not cleaned_value:
        return default

    return cleaned_value


def _read_int(name: str, default: int) -> int:
    """Read one setting as an integer."""
    raw_value = _read_raw_setting(name)
    if raw_value is None:
        return default

    cleaned_value = raw_value.strip()
    if not cleaned_value:
        return default

    try:
        return int(cleaned_value)
    except ValueError:
        return default


def _read_raw_setting(name: str) -> str | None:
    """Read from the real environment first, then local .env."""
    value = os.getenv(name)
    if value is not None:
        return value

    return _read_dotenv_values().get(name)


@lru_cache(maxsize=1)
def _read_dotenv_values() -> dict[str, str]:
    """Read simple KEY=VALUE lines from the project .env file."""
    if os.getenv("SIGHTLINE_IGNORE_DOTENV") == "1":
        return {}

    dotenv_path = _dotenv_path()
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        cleaned_line = line.strip()
        if not cleaned_line:
            continue

        if cleaned_line.startswith("#"):
            continue

        if "=" not in cleaned_line:
            continue

        key, raw_value = cleaned_line.split("=", maxsplit=1)
        cleaned_key = key.strip()
        if not cleaned_key:
            continue

        values[cleaned_key] = _clean_dotenv_value(raw_value)

    return values


def _dotenv_path() -> Path:
    """Return the configured .env path or the repo-local default."""
    custom_path = os.getenv("SIGHTLINE_DOTENV_PATH")
    if custom_path:
        return Path(custom_path).expanduser()

    return Path(__file__).resolve().parent.parent / ".env"


def _clean_dotenv_value(value: str) -> str:
    """Trim whitespace and one optional quote pair from a .env value."""
    cleaned_value = value.strip()
    if len(cleaned_value) < 2:
        return cleaned_value

    if cleaned_value[0] == cleaned_value[-1] and cleaned_value[0] in {"'", '"'}:
        return cleaned_value[1:-1]

    return cleaned_value


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


def _clear_settings_cache() -> None:
    """Clear cached environment and .env reads."""
    _build_cached_settings.cache_clear()
    _read_dotenv_values.cache_clear()


get_settings.cache_clear = _clear_settings_cache
