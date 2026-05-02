"""Tests for environment-based settings."""

from __future__ import annotations

import os

import pytest

from backend.schemas.error_codes import ErrorCode
from backend.settings import Settings
from backend.settings import get_settings
from backend.settings import get_validated_settings
from backend.settings import validate_settings


def test_settings_use_defaults_when_env_is_missing() -> None:
    """Missing environment variables should fall back to simple defaults."""
    os.environ.pop("APP_NAME", None)
    os.environ.pop("APP_ENV", None)
    os.environ.pop("REQUEST_TIMEOUT_SECONDS", None)
    os.environ.pop("MAX_REQUEST_BYTES", None)
    os.environ.pop("RATE_LIMIT_PER_MINUTE", None)
    os.environ.pop("RAW_STORAGE_PATH", None)
    os.environ.pop("AUDIT_LOG_PATH", None)
    os.environ.pop("API_AUTH_TOKEN", None)
    os.environ.pop("GRAPH_REPOSITORY_KIND", None)
    os.environ.pop("NEO4J_URL", None)
    os.environ.pop("NEO4J_USERNAME", None)
    os.environ.pop("NEO4J_PASSWORD", None)
    os.environ.pop("IPINFO_API_KEY", None)

    settings = get_settings()

    assert settings.app_name == "SightlineOSINT"
    assert settings.app_env == "development"
    assert settings.request_timeout_seconds == 30
    assert settings.max_request_bytes == 1_000_000
    assert settings.rate_limit_per_minute == 120
    assert settings.raw_storage_path == "data/raw"
    assert settings.audit_log_path == "data/audit.log"
    assert settings.api_auth_token == ""
    assert settings.graph_repository_kind == "memory"
    assert settings.neo4j_url == "bolt://localhost:7687"
    assert settings.neo4j_username == ""
    assert settings.neo4j_password == ""
    assert settings.ipinfo_api_key == ""


def test_settings_use_environment_overrides() -> None:
    """Environment variables should override the defaults."""
    os.environ["APP_NAME"] = "SightlineOSINT Test"
    os.environ["APP_ENV"] = "test"
    os.environ["REQUEST_TIMEOUT_SECONDS"] = "45"
    os.environ["MAX_REQUEST_BYTES"] = "2048"
    os.environ["RATE_LIMIT_PER_MINUTE"] = "10"
    os.environ["RAW_STORAGE_PATH"] = "tmp/raw"
    os.environ["AUDIT_LOG_PATH"] = "tmp/audit.log"
    os.environ["API_AUTH_TOKEN"] = "test-token"
    os.environ["GRAPH_REPOSITORY_KIND"] = "neo4j"
    os.environ["NEO4J_URL"] = "bolt://graph.example:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = "password"
    os.environ["IPINFO_API_KEY"] = "secret-key"

    settings = get_settings()

    assert settings.app_name == "SightlineOSINT Test"
    assert settings.app_env == "test"
    assert settings.request_timeout_seconds == 45
    assert settings.max_request_bytes == 2048
    assert settings.rate_limit_per_minute == 10
    assert settings.raw_storage_path == "tmp/raw"
    assert settings.audit_log_path == "tmp/audit.log"
    assert settings.api_auth_token == "test-token"
    assert settings.graph_repository_kind == "neo4j"
    assert settings.neo4j_url == "bolt://graph.example:7687"
    assert settings.neo4j_username == "neo4j"
    assert settings.neo4j_password == "password"
    assert settings.ipinfo_api_key == "secret-key"


def test_settings_can_read_local_dotenv_file(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Local .env values should work when the shell has not exported them."""
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "APP_NAME=Sightline Dotenv",
                "REQUEST_TIMEOUT_SECONDS=12",
                "IPINFO_API_KEY=dotenv-key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("REQUEST_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("IPINFO_API_KEY", raising=False)
    monkeypatch.delenv("SIGHTLINE_IGNORE_DOTENV", raising=False)
    monkeypatch.setenv("SIGHTLINE_DOTENV_PATH", str(dotenv_path))
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "Sightline Dotenv"
    assert settings.request_timeout_seconds == 12
    assert settings.ipinfo_api_key == "dotenv-key"


def test_validate_settings_rejects_non_positive_timeout() -> None:
    """Startup validation should reject zero or negative timeouts."""
    with pytest.raises(ValueError, match=ErrorCode.INVALID_SETTINGS.value):
        validate_settings(
            Settings(
                request_timeout_seconds=0,
            )
        )


def test_validate_settings_rejects_blank_raw_storage_path() -> None:
    """Startup validation should reject missing storage paths."""
    with pytest.raises(ValueError, match=ErrorCode.INVALID_SETTINGS.value):
        validate_settings(
            Settings(
                raw_storage_path="   ",
            )
        )


def test_validate_settings_rejects_non_positive_request_size_limit() -> None:
    """Startup validation should reject impossible request size limits."""
    with pytest.raises(ValueError, match=ErrorCode.INVALID_SETTINGS.value):
        validate_settings(
            Settings(
                max_request_bytes=0,
            )
        )


def test_validate_settings_rejects_non_positive_rate_limit() -> None:
    """Startup validation should reject impossible rate limits."""
    with pytest.raises(ValueError, match=ErrorCode.INVALID_SETTINGS.value):
        validate_settings(
            Settings(
                rate_limit_per_minute=0,
            )
        )


def test_validate_settings_rejects_unknown_graph_repository_kind() -> None:
    """Startup validation should reject unknown graph repository modes."""
    with pytest.raises(ValueError, match=ErrorCode.INVALID_SETTINGS.value):
        validate_settings(
            Settings(
                graph_repository_kind="postgres",
            )
        )


def test_get_validated_settings_rejects_invalid_environment_values() -> None:
    """Validated settings should fail fast on impossible startup values."""
    os.environ["REQUEST_TIMEOUT_SECONDS"] = "-5"

    with pytest.raises(ValueError, match=ErrorCode.INVALID_SETTINGS.value):
        get_validated_settings()
