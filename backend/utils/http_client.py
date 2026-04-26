"""Tiny HTTP helpers for live provider calls."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen


@dataclass(frozen=True)
class JSONResponse:
    """Small container for one JSON HTTP response."""

    status_code: int
    data: Any
    url: str


class HTTPClientError(Exception):
    """Raised when an HTTP request fails cleanly."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        failure_kind: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.failure_kind = failure_kind


def _build_url(url: str, params: dict[str, Any] | None = None) -> str:
    """Add query params to a base URL when needed."""
    if not params:
        return url

    query_string = urlencode(params, doseq=True)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query_string}"


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 30,
    opener: Any = None,
) -> JSONResponse:
    """Fetch one URL and parse its JSON body."""
    request_url = _build_url(url, params=params)
    request = Request(request_url, headers=headers or {}, method="GET")
    open_request = opener or urlopen

    try:
        with open_request(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            status_code = response.getcode()
    except HTTPError as error:
        raise HTTPClientError(
            f"HTTP request failed with status {error.code}.",
            status_code=error.code,
            failure_kind="http_error",
        ) from error
    except URLError as error:
        raise HTTPClientError(
            f"Network request failed: {error.reason}",
            failure_kind="network_error",
        ) from error
    except TimeoutError as error:
        raise HTTPClientError(
            "Network request timed out.",
            failure_kind="timeout",
        ) from error

    try:
        response_data = json.loads(response_body)
    except json.JSONDecodeError as error:
        raise HTTPClientError(
            "Provider returned invalid JSON.",
            failure_kind="invalid_json",
        ) from error

    return JSONResponse(
        status_code=status_code,
        data=response_data,
        url=request_url,
    )
