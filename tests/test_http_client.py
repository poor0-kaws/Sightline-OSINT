"""Tests for the tiny HTTP client helper."""

from __future__ import annotations

from urllib.error import HTTPError

import pytest

from backend.utils.http_client import get_json
from backend.utils.http_client import HTTPClientError


class FakeHTTPResponse:
    """Small fake response object for HTTP client tests."""

    def __init__(self, body: str, status_code: int = 200) -> None:
        self.body = body
        self.status_code = status_code

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body.encode("utf-8")

    def getcode(self) -> int:
        return self.status_code


def test_get_json_builds_url_and_parses_json() -> None:
    """The HTTP client should send params and parse the JSON body."""
    captured_request = {}

    def fake_opener(request, timeout):
        captured_request["url"] = request.full_url
        captured_request["timeout"] = timeout
        captured_request["accept"] = request.headers.get("Accept")
        return FakeHTTPResponse('{"ip":"8.8.8.8"}', status_code=200)

    response = get_json(
        "https://ipinfo.io/8.8.8.8/json",
        params={"token": "secret-key"},
        headers={"Accept": "application/json"},
        timeout_seconds=12,
        opener=fake_opener,
    )

    assert captured_request["url"] == "https://ipinfo.io/8.8.8.8/json?token=secret-key"
    assert captured_request["timeout"] == 12
    assert captured_request["accept"] == "application/json"
    assert response.status_code == 200
    assert response.data["ip"] == "8.8.8.8"


def test_get_json_raises_clean_error_for_http_failures() -> None:
    """HTTP errors should become readable client errors."""

    def fake_opener(request, timeout):
        raise HTTPError(
            url=request.full_url,
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        )

    with pytest.raises(HTTPClientError) as error:
        get_json("https://example.com/data", opener=fake_opener)

    assert error.value.status_code == 429


def test_get_json_raises_clean_error_for_invalid_json() -> None:
    """Broken JSON should produce a readable parse error."""

    def fake_opener(request, timeout):
        return FakeHTTPResponse("not-json", status_code=200)

    with pytest.raises(HTTPClientError) as error:
        get_json("https://example.com/data", opener=fake_opener)

    assert "invalid JSON" in str(error.value)
