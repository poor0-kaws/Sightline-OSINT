"""FastAPI app for the current SightlineOSINT backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.relationships import extract_relationships_from_normalized_record
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceKind
from backend.schemas.ingestion import SourceRequest
from backend.services.ingestion_service import IngestionService
from backend.services.provider_processing_pipeline import ProviderProcessingPipeline
from backend.settings import Settings
from backend.settings import get_validated_settings
from backend.storage import list_raw_responses
from backend.storage import load_raw_response


def build_app(
    *,
    settings: Settings | None = None,
    ingestion_service: IngestionService | None = None,
    processing_pipeline: ProviderProcessingPipeline | None = None,
) -> FastAPI:
    """Build the FastAPI app on top of the current backend services."""
    app_settings = settings or get_validated_settings()
    service = ingestion_service or IngestionService()
    pipeline = processing_pipeline or ProviderProcessingPipeline(ingestion_service=service)

    app = FastAPI(title=app_settings.app_name)

    @app.exception_handler(APIError)
    async def handle_api_error(_request: Request, error: APIError) -> JSONResponse:
        """Turn expected API errors into the shared error shape."""
        return _json_response(
            {"error": {"code": error.code, "message": error.message}},
            status_code=error.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
        """Never leak raw server exceptions to API callers."""
        return _json_response(
            {"error": {"code": "internal_server_error", "message": "Unexpected API error."}},
            status_code=500,
        )

    @app.get("/")
    async def root() -> JSONResponse:
        """Return a tiny API summary payload."""
        return _json_response(_build_root_payload(app_settings))

    @app.get("/health")
    async def health() -> JSONResponse:
        """Return a tiny health payload."""
        return _json_response(_build_health_payload(app_settings))

    @app.get("/providers")
    async def providers() -> JSONResponse:
        """Return supported provider definitions."""
        return _json_response({"providers": service.list_supported_providers()})

    @app.get("/providers/{provider}/preview")
    async def provider_preview(provider: str) -> JSONResponse:
        """Return one sample raw response for a provider."""
        parsed_provider = _parse_provider_text(provider)
        return _json_response({"preview": service.preview_provider_response(parsed_provider)})

    @app.get("/records/raw")
    async def raw_records() -> JSONResponse:
        """Return all saved raw records."""
        return _json_response({"records": list_raw_responses()})

    @app.get("/records/raw/{record_id}")
    async def raw_record(record_id: str) -> JSONResponse:
        """Return one saved raw record by id."""
        cleaned_record_id = record_id.strip()
        if not cleaned_record_id:
            raise APIError(400, "missing_record_id", "Record id is required.")

        try:
            saved_raw_record = load_raw_response(cleaned_record_id)
        except FileNotFoundError as error:
            raise APIError(404, "raw_record_not_found", str(error)) from error

        return _json_response({"record": saved_raw_record})

    @app.post("/source/raw")
    async def source_raw(request: Request) -> JSONResponse:
        """Run one raw source request and return the raw response plus save details."""
        source_request = _parse_source_request(await _read_json_body(request), app_settings)
        raw_response, saved_raw_record = service.run_source_request_with_record(source_request)
        return _json_response(
            {
                "response": raw_response,
                "saved_raw_record_id": saved_raw_record.record_id if saved_raw_record is not None else "",
            }
        )

    @app.post("/source/normalized")
    async def source_normalized(request: Request) -> JSONResponse:
        """Run one fetch-save-normalize request."""
        source_request = _parse_source_request(await _read_json_body(request), app_settings)
        return _json_response({"record": pipeline.run(source_request)})

    @app.post("/source/relationships")
    async def source_relationships(request: Request) -> JSONResponse:
        """Run one fetch-save-normalize-relationships request."""
        source_request = _parse_source_request(await _read_json_body(request), app_settings)
        normalized_record = pipeline.run(source_request)
        relationship_result = extract_relationships_from_normalized_record(normalized_record)
        return _json_response(
            {
                "record": normalized_record,
                "relationships": relationship_result,
            }
        )

    return app


class APIError(Exception):
    """Small structured API error."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


async def _read_json_body(request: Request) -> object:
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


def _build_root_payload(settings: Settings) -> dict[str, Any]:
    """Return a tiny API summary payload."""
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "api_status": "ready",
        "routes": [
            "/health",
            "/providers",
            "/providers/{provider}/preview",
            "/records/raw",
            "/records/raw/{record_id}",
            "/source/raw",
            "/source/normalized",
            "/source/relationships",
        ],
    }


def _build_health_payload(settings: Settings) -> dict[str, Any]:
    """Return a tiny health response."""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "raw_storage_path": settings.raw_storage_path,
        "raw_storage_exists": Path(settings.raw_storage_path).exists(),
    }


def _parse_source_request(payload: object, settings: Settings) -> SourceRequest:
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

    provider = _parse_provider_text(source_payload.get("provider"))
    source_kind = _parse_source_kind_text(source_payload.get("source_kind", SourceKind.API.value))
    source_id = _clean_text(source_payload.get("source_id")) or "api-source"
    location = _clean_text(source_payload.get("location")) or _default_location_for_provider(provider)
    display_name = _clean_text(source_payload.get("display_name")) or provider.value
    timeout_seconds = _parse_timeout_value(source_payload.get("timeout_seconds"), settings.request_timeout_seconds)

    return SourceRequest(
        source=SourceConfig(
            source_id=source_id,
            source_kind=source_kind,
            provider=provider,
            location=location,
            display_name=display_name,
            timeout_seconds=timeout_seconds,
        ),
        query=payload.get("query"),
    )


def _parse_provider_text(value: object) -> ProviderKind:
    """Turn provider text into a strict provider enum."""
    cleaned_value = _clean_text(value).lower()
    if not cleaned_value:
        raise APIError(400, "invalid_provider", "Provider is required.")

    try:
        return ProviderKind(cleaned_value)
    except ValueError as error:
        raise APIError(400, "invalid_provider", f"Unsupported provider: {cleaned_value}") from error


def _parse_source_kind_text(value: object) -> SourceKind:
    """Turn source-kind text into a strict source-kind enum."""
    cleaned_value = _clean_text(value).lower()
    if not cleaned_value:
        return SourceKind.API

    try:
        return SourceKind(cleaned_value)
    except ValueError as error:
        raise APIError(400, "invalid_source_kind", f"Unsupported source_kind: {cleaned_value}") from error


def _parse_timeout_value(value: object, default_value: int) -> int:
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


def _default_location_for_provider(provider: ProviderKind) -> str:
    """Return one simple default location for a provider."""
    if provider == ProviderKind.IPINFO:
        return "https://ipinfo.io"
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


def _clean_text(value: object) -> str:
    """Return one safe stripped string."""
    if not isinstance(value, str):
        return ""

    return value.strip()


def _json_response(payload: object, *, status_code: int = 200) -> JSONResponse:
    """Return one JSON response using the repo's own serializer rules."""
    return JSONResponse(content=_to_json_value(payload), status_code=status_code)


def _to_json_value(value: object) -> object:
    """Turn models and enums into JSON-safe values."""
    if hasattr(value, "model_dump"):
        return _to_json_value(value.model_dump())

    if hasattr(value, "value"):
        enum_value = getattr(value, "value", None)
        if isinstance(enum_value, (str, int, float, bool)) or enum_value is None:
            return enum_value

    if isinstance(value, dict):
        return {str(key): _to_json_value(nested_value) for key, nested_value in value.items()}

    if isinstance(value, list):
        return [_to_json_value(item) for item in value]

    return value
