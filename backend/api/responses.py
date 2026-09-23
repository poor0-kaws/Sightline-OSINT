"""Shared HTTP response and error helpers for the API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.responses import JSONResponse

from backend.settings import Settings


class APIError(Exception):
    """Small structured API error."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def json_response(payload: object, *, status_code: int = 200) -> JSONResponse:
    """Return one JSON response using the repo's own serializer rules."""
    return JSONResponse(content=to_json_value(payload), status_code=status_code)


def to_json_value(value: object) -> object:
    """Turn models and enums into JSON-safe values."""
    if hasattr(value, "model_dump"):
        return to_json_value(value.model_dump())

    if hasattr(value, "value"):
        enum_value = getattr(value, "value", None)
        if isinstance(enum_value, (str, int, float, bool)) or enum_value is None:
            return enum_value

    if isinstance(value, dict):
        return {str(key): to_json_value(nested_value) for key, nested_value in value.items()}

    if isinstance(value, list):
        return [to_json_value(item) for item in value]

    return value


def build_root_payload(settings: Settings) -> dict[str, Any]:
    """Return a tiny API summary payload."""
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "api_status": "ready",
        "routes": [
            "/health",
            "/providers",
            "/providers/{provider}/preview",
            "/cases",
            "/records/raw",
            "/records/raw/{record_id}",
            "/resolution/matches",
            "/source/raw",
            "/source/resolution",
            "/source/normalized",
            "/source/relationships",
            "/source/graph",
            "/source/full",
            "/graph/data",
            "/graph/status",
            "/graph/rebuild",
            "/app",
            "/app/graph-data",
        ],
    }


def build_health_payload(settings: Settings) -> dict[str, Any]:
    """Return a tiny health response."""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "raw_storage_path": settings.raw_storage_path,
        "raw_storage_exists": Path(settings.raw_storage_path).exists(),
    }
