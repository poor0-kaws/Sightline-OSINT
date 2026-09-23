"""Request parsing helpers for the API."""

from __future__ import annotations

import json

from fastapi import Request

from backend.api.responses import APIError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceKind
from backend.schemas.ingestion import SourceRequest
from backend.settings import Settings


async def read_json_body(request: Request) -> object:
    """Read and parse one JSON request body."""
    try:
        raw_body = await request.body()
    except Exception as error:
        raise APIError(400, "bad_json", f"Request body must contain valid JSON. {error}") from error

    if not raw_body:
        raise APIError(400, "bad_json", "Request body must contain valid JSON.")

    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise APIError(400, "bad_json", f"Request body must contain valid JSON. {error}") from error


def parse_source_request(payload: object, settings: Settings) -> SourceRequest:
    """Turn JSON input into one strict SourceRequest object."""
    if not isinstance(payload, dict):
        raise APIError(400, "invalid_request_body", "Request body must be a JSON object.")

    if "source" not in payload:
        raise APIError(400, "missing_source", "Request body must include a source object.")

    if "query" not in payload:
        raise APIError(400, "missing_query", "Request body must include a query field.")

    source_payload = payload.get("source")
    if not isinstance(source_payload, dict):
        raise APIError(400, "invalid_source", "Source must be a JSON object.")

    provider = parse_provider_text(source_payload.get("provider"))
    source_kind = parse_source_kind_text(source_payload.get("source_kind", SourceKind.API.value))
    source_id = _clean_text(source_payload.get("source_id")) or "api-source"
    case_id = _clean_text(source_payload.get("case_id")) or "default"
    location = _clean_text(source_payload.get("location")) or default_location_for_provider(provider)
    display_name = _clean_text(source_payload.get("display_name")) or provider.value
    timeout_seconds = parse_timeout_value(source_payload.get("timeout_seconds"), settings.request_timeout_seconds)

    return SourceRequest(
        source=SourceConfig(
            source_id=source_id,
            case_id=case_id,
            source_kind=source_kind,
            provider=provider,
            location=location,
            display_name=display_name,
            timeout_seconds=timeout_seconds,
        ),
        query=payload.get("query"),
    )


def parse_provider_text(value: object) -> ProviderKind:
    """Turn provider text into a strict provider enum."""
    cleaned_value = _clean_text(value).lower()
    if not cleaned_value:
        raise APIError(400, "invalid_provider", "Provider is required.")

    try:
        return ProviderKind(cleaned_value)
    except ValueError as error:
        raise APIError(400, "invalid_provider", f"Unsupported provider: {cleaned_value}") from error


def parse_source_kind_text(value: object) -> SourceKind:
    """Turn source-kind text into a strict source-kind enum."""
    cleaned_value = _clean_text(value).lower()
    if not cleaned_value:
        return SourceKind.API

    try:
        return SourceKind(cleaned_value)
    except ValueError as error:
        raise APIError(400, "invalid_source_kind", f"Unsupported source_kind: {cleaned_value}") from error


def parse_timeout_value(value: object, default_value: int) -> int:
    """Turn timeout input into one safe positive integer."""
    if value is None:
        return default_value

    if isinstance(value, bool):
        raise APIError(400, "invalid_timeout", "timeout_seconds must be a positive integer.")

    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as error:
        raise APIError(400, "invalid_timeout", "timeout_seconds must be a positive integer.") from error

    if parsed_value <= 0:
        raise APIError(400, "invalid_timeout", "timeout_seconds must be a positive integer.")

    return parsed_value


def default_location_for_provider(provider: ProviderKind) -> str:
    """Return one simple default location for a provider."""
    if provider == ProviderKind.IPINFO:
        return "https://api.ipinfo.io/lite"
    if provider == ProviderKind.CRT_SH:
        return "https://crt.sh"
    if provider == ProviderKind.NOMINATIM:
        return "https://nominatim.openstreetmap.org"
    if provider == ProviderKind.OPENSKY:
        return "https://opensky-network.org"
    if provider == ProviderKind.WEBHOOK:
        return "webhook://local"
    if provider == ProviderKind.CSV_UPLOAD:
        return "csv://upload"
    if provider == ProviderKind.MANUAL_INPUT:
        return "manual://input"
    return ""


def case_id_from_request(request: Request) -> str:
    """Read an optional case id query parameter."""
    return _clean_text(request.query_params.get("case_id"))


def _clean_text(value: object) -> str:
    """Return one safe stripped string."""
    if not isinstance(value, str):
        return ""

    return value.strip()
