"""Request guardrails and audit logging for the API."""

from __future__ import annotations

import json
from pathlib import Path
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.api.parsing import case_id_from_request
from backend.api.responses import json_response
from backend.settings import Settings
from backend.utils.time import utc_now_iso


def check_request_size(request: Request, settings: Settings) -> JSONResponse | None:
    """Reject requests that are too large before parsing JSON."""
    content_length = _parse_content_length(request.headers.get("content-length"))
    if content_length <= settings.max_request_bytes:
        return None

    return json_response(
        {
            "error": {
                "code": "request_too_large",
                "message": f"Request body must be {settings.max_request_bytes} bytes or smaller.",
            }
        },
        status_code=413,
    )


def check_auth(request: Request, settings: Settings) -> JSONResponse | None:
    """Require a bearer token when API_AUTH_TOKEN is configured."""
    if not settings.api_auth_token:
        return None

    if _is_public_path(request.url.path):
        return None

    expected_header = f"Bearer {settings.api_auth_token}"
    if request.headers.get("authorization") == expected_header:
        return None

    return json_response(
        {"error": {"code": "unauthorized", "message": "A valid bearer token is required."}},
        status_code=401,
    )


def check_rate_limit(
    request: Request,
    settings: Settings,
    rate_limit_state: dict[str, list[float]],
) -> JSONResponse | None:
    """Apply a small per-client in-memory rate limit."""
    client_id = request.client.host if request.client is not None else "unknown"
    current_time = time.time()
    window_start = current_time - 60
    recent_requests = [
        timestamp
        for timestamp in rate_limit_state.get(client_id, [])
        if timestamp >= window_start
    ]

    if len(recent_requests) >= settings.rate_limit_per_minute:
        rate_limit_state[client_id] = recent_requests
        return json_response(
            {"error": {"code": "rate_limited", "message": "Too many requests. Try again later."}},
            status_code=429,
        )

    recent_requests.append(current_time)
    rate_limit_state[client_id] = recent_requests
    return None


def write_audit_log(
    settings: Settings,
    *,
    request: Request,
    status_code: int,
    error_code: str = "",
) -> None:
    """Append one JSONL audit event without breaking the request path."""
    try:
        audit_path = Path(settings.audit_log_path)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_event = {
            "at": utc_now_iso(),
            "method": request.method,
            "path": request.url.path,
            "case_id": case_id_from_request(request),
            "status_code": status_code,
            "error_code": error_code,
        }
        with audit_path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(audit_event, sort_keys=True) + "\n")
    except Exception:
        return


def _parse_content_length(value: object) -> int:
    """Read a content-length header safely."""
    if not isinstance(value, str):
        return 0

    try:
        return int(value)
    except ValueError:
        return 0


def _is_public_path(path: str) -> bool:
    """Return true for browser/static paths that remain public."""
    return path in {"/app", "/health"} or path.startswith("/app/assets")
