"""Tests for environment-based settings."""

from __future__ import annotations

import os

from backend.settings import get_settings


def test_settings_use_defaults_when_env_is_missing() -> None:
    """Missing environment variables should fall back to simple defaults."""
    os.environ.pop("APP_NAME", None)
    os.environ.pop("APP_ENV", None)
    os.environ.pop("REQUEST_TIMEOUT_SECONDS", None)
    os.environ.pop("RAW_STORAGE_PATH", None)
    os.environ.pop("NEO4J_URL", None)
    os.environ.pop("IPINFO_API_KEY", None)

    settings = get_settings()

    assert settings.app_name == "SightlineOSINT"
    assert settings.app_env == "development"
    assert settings.request_timeout_seconds == 30
    assert settings.raw_storage_path == "data/raw"
    assert settings.neo4j_url == "bolt://localhost:7687"
    assert settings.ipinfo_api_key == ""


def test_settings_use_environment_overrides() -> None:
    """Environment variables should override the defaults."""
    os.environ["APP_NAME"] = "SightlineOSINT Test"
    os.environ["APP_ENV"] = "test"
    os.environ["REQUEST_TIMEOUT_SECONDS"] = "45"
    os.environ["RAW_STORAGE_PATH"] = "tmp/raw"
    os.environ["NEO4J_URL"] = "bolt://graph.example:7687"
    os.environ["IPINFO_API_KEY"] = "secret-key"

    settings = get_settings()

    assert settings.app_name == "SightlineOSINT Test"
    assert settings.app_env == "test"
    assert settings.request_timeout_seconds == 45
    assert settings.raw_storage_path == "tmp/raw"
    assert settings.neo4j_url == "bolt://graph.example:7687"
    assert settings.ipinfo_api_key == "secret-key"
