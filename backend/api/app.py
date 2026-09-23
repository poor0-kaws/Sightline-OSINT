"""FastAPI app for the current SightlineOSINT backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.graph_workspace import build_graph_workspace_payload_from_snapshot
from backend.api.parsing import case_id_from_request
from backend.api.parsing import parse_provider_text
from backend.api.parsing import parse_source_request
from backend.api.parsing import read_json_body
from backend.api.responses import APIError
from backend.api.responses import build_health_payload
from backend.api.responses import build_root_payload
from backend.api.responses import json_response
from backend.api.security import check_auth
from backend.api.security import check_rate_limit
from backend.api.security import check_request_size
from backend.api.security import write_audit_log
from backend.cases import build_case_summaries
from backend.graph import GraphWriteService
from backend.graph import build_graph_repository
from backend.graph.repository import GraphRepositoryProtocol
from backend.relationships import extract_relationships_from_normalized_record
from backend.resolution import resolve_saved_raw_records
from backend.services.graph_processing_pipeline import GraphProcessingPipeline
from backend.services.graph_rebuild_service import rebuild_graph_from_saved_raw_records
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
    graph_repository: GraphRepositoryProtocol | None = None,
    graph_processing_pipeline: GraphProcessingPipeline | None = None,
) -> FastAPI:
    """Build the FastAPI app on top of the current backend services."""
    app_settings = settings or get_validated_settings()
    service = ingestion_service or IngestionService()
    pipeline = processing_pipeline or ProviderProcessingPipeline(ingestion_service=service)
    repository = graph_repository or build_graph_repository(app_settings)
    graph_write_service = GraphWriteService(repository)
    graph_pipeline = graph_processing_pipeline or GraphProcessingPipeline(
        repository=repository,
        provider_processing_pipeline=pipeline,
        graph_write_service=graph_write_service,
    )
    frontend_directory = Path(__file__).parent / "static" / "react"
    frontend_assets_directory = frontend_directory / "assets"
    frontend_index_path = frontend_directory / "index.html"

    app = FastAPI(title=app_settings.app_name)
    app.mount("/app/assets", StaticFiles(directory=frontend_assets_directory, check_dir=False), name="app-assets")
    rate_limit_state: dict[str, list[float]] = {}

    @app.middleware("http")
    async def protect_api(request: Request, call_next: object) -> object:
        """Apply simple production guardrails before route handlers run."""
        size_error = check_request_size(request, app_settings)
        if size_error is not None:
            write_audit_log(app_settings, request=request, status_code=413, error_code="request_too_large")
            return size_error

        auth_error = check_auth(request, app_settings)
        if auth_error is not None:
            write_audit_log(app_settings, request=request, status_code=401, error_code="unauthorized")
            return auth_error

        rate_limit_error = check_rate_limit(request, app_settings, rate_limit_state)
        if rate_limit_error is not None:
            write_audit_log(app_settings, request=request, status_code=429, error_code="rate_limited")
            return rate_limit_error

        response = await call_next(request)
        write_audit_log(app_settings, request=request, status_code=response.status_code)
        return response

    @app.exception_handler(APIError)
    async def handle_api_error(_request: Request, error: APIError) -> JSONResponse:
        """Turn expected API errors into the shared error shape."""
        return json_response(
            {"error": {"code": error.code, "message": error.message}},
            status_code=error.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
        """Never leak raw server exceptions to API callers."""
        return json_response(
            {"error": {"code": "internal_server_error", "message": "Unexpected API error."}},
            status_code=500,
        )

    @app.get("/")
    async def root() -> JSONResponse:
        """Return a tiny API summary payload."""
        return json_response(build_root_payload(app_settings))

    @app.get("/app")
    async def frontend() -> FileResponse:
        """Serve the investigation workspace frontend."""
        if not frontend_index_path.exists():
            raise APIError(503, "frontend_not_built", "Frontend bundle is missing. Build the React app first.")

        return FileResponse(frontend_index_path)

    @app.get("/app/graph-data")
    async def graph_data(request: Request) -> JSONResponse:
        """Return graph workspace data built from saved raw records."""
        case_id = case_id_from_request(request)
        saved_raw_records = list_raw_responses(case_id=case_id)
        graph_snapshot = repository.read_graph(case_id=case_id)
        if saved_raw_records and not graph_snapshot.nodes:
            rebuild_graph_from_saved_raw_records(
                saved_raw_records=saved_raw_records,
                graph_write_service=graph_write_service,
            )
            graph_snapshot = repository.read_graph(case_id=case_id)

        return json_response(
            build_graph_workspace_payload_from_snapshot(
                settings=app_settings,
                saved_raw_records=saved_raw_records,
                graph_snapshot=graph_snapshot,
            )
        )

    @app.get("/health")
    async def health() -> JSONResponse:
        """Return a tiny health payload."""
        return json_response(build_health_payload(app_settings))

    @app.get("/providers")
    async def providers() -> JSONResponse:
        """Return supported provider definitions."""
        return json_response({"providers": service.list_supported_providers()})

    @app.get("/providers/{provider}/preview")
    async def provider_preview(provider: str) -> JSONResponse:
        """Return one sample raw response for a provider."""
        parsed_provider = parse_provider_text(provider)
        return json_response({"preview": service.preview_provider_response(parsed_provider)})

    @app.get("/cases")
    async def cases() -> JSONResponse:
        """Return known investigation cases from saved raw records."""
        return json_response({"cases": build_case_summaries(list_raw_responses())})

    @app.get("/records/raw")
    async def raw_records(request: Request) -> JSONResponse:
        """Return all saved raw records."""
        return json_response({"records": list_raw_responses(case_id=case_id_from_request(request))})

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

        return json_response({"record": saved_raw_record})

    @app.get("/resolution/matches")
    async def resolution_matches(request: Request) -> JSONResponse:
        """Resolve comparable entities across saved raw records."""
        return json_response(
            {"resolution": resolve_saved_raw_records(list_raw_responses(case_id=case_id_from_request(request)))}
        )

    @app.post("/source/raw")
    async def source_raw(request: Request) -> JSONResponse:
        """Run one raw source request and return the raw response plus save details."""
        source_request = parse_source_request(await read_json_body(request), app_settings)
        raw_response, saved_raw_record = service.run_source_request_with_record(source_request)
        return json_response(
            {
                "response": raw_response,
                "saved_raw_record_id": saved_raw_record.record_id if saved_raw_record is not None else "",
            }
        )

    @app.post("/source/resolution")
    async def source_resolution(request: Request) -> JSONResponse:
        """Run one source request, then resolve it against saved records."""
        source_request = parse_source_request(await read_json_body(request), app_settings)
        normalized_record = pipeline.run(source_request)
        return json_response(
            {
                "record": normalized_record,
                "resolution": resolve_saved_raw_records(
                    list_raw_responses(case_id=source_request.source.case_id)
                ),
            }
        )

    @app.post("/source/normalized")
    async def source_normalized(request: Request) -> JSONResponse:
        """Run one fetch-save-normalize request."""
        source_request = parse_source_request(await read_json_body(request), app_settings)
        return json_response({"record": pipeline.run(source_request)})

    @app.post("/source/relationships")
    async def source_relationships(request: Request) -> JSONResponse:
        """Run one fetch-save-normalize-relationships request."""
        source_request = parse_source_request(await read_json_body(request), app_settings)
        normalized_record = pipeline.run(source_request)
        relationship_result = extract_relationships_from_normalized_record(normalized_record)
        return json_response(
            {
                "record": normalized_record,
                "relationships": relationship_result,
            }
        )

    @app.post("/source/graph")
    async def source_graph(request: Request) -> JSONResponse:
        """Run one fetch-save-normalize-relationships-graph-write request."""
        source_request = parse_source_request(await read_json_body(request), app_settings)
        return json_response({"graph_write": graph_pipeline.run(source_request)})

    @app.post("/source/full")
    async def source_full(request: Request) -> JSONResponse:
        """Run ingest, normalize, resolve, relationships, graph write, and graph read."""
        source_request = parse_source_request(await read_json_body(request), app_settings)
        normalized_record = pipeline.run(source_request)
        relationship_result = extract_relationships_from_normalized_record(normalized_record)
        graph_write = graph_write_service.write_graph_artifacts(normalized_record, relationship_result)
        saved_raw_records = list_raw_responses(case_id=source_request.source.case_id)
        graph_snapshot = repository.read_graph(case_id=source_request.source.case_id)
        return json_response(
            {
                "record": normalized_record,
                "resolution": resolve_saved_raw_records(saved_raw_records),
                "relationships": relationship_result,
                "graph_write": graph_write,
                "graph": graph_snapshot,
            }
        )

    @app.get("/graph/data")
    async def graph_raw_data(request: Request) -> JSONResponse:
        """Return raw graph repository data for tools and tests."""
        return json_response({"graph": repository.read_graph(case_id=case_id_from_request(request))})

    @app.get("/graph/status")
    async def graph_status(request: Request) -> JSONResponse:
        """Return graph repository status counts."""
        graph_snapshot = repository.read_graph(case_id=case_id_from_request(request))
        return json_response(
            {
                "graph_repository_kind": app_settings.graph_repository_kind,
                "nodes": len(graph_snapshot.nodes),
                "relationships": len(graph_snapshot.relationships),
            }
        )

    @app.post("/graph/rebuild")
    async def graph_rebuild(request: Request) -> JSONResponse:
        """Replay saved raw records into the configured graph repository."""
        case_id = case_id_from_request(request)
        return json_response(
            {
                "graph_rebuild": rebuild_graph_from_saved_raw_records(
                    saved_raw_records=list_raw_responses(case_id=case_id),
                    graph_write_service=graph_write_service,
                )
            }
        )

    return app
