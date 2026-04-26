"""API and scraper-backed source adapters from the architecture note."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from backend.connectors.base import BaseSourceAdapter
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import QueryType
from backend.schemas.ingestion import SourceKind
from backend.settings import get_settings
from backend.utils.http_client import get_json
from backend.utils.http_client import HTTPClientError
from backend.utils.validation import has_valid_bounding_box
from backend.utils.validation import has_valid_coordinates
from backend.utils.validation import get_crt_sh_query_error
from backend.utils.validation import is_valid_aircraft_id
from backend.utils.validation import is_valid_domain_name
from backend.utils.validation import is_valid_ipv4_address
from backend.utils.validation import is_valid_place_name


class IPinfoAdapter(BaseSourceAdapter):
    """Adapter for IP intelligence lookups."""

    provider = ProviderKind.IPINFO
    source_kind = SourceKind.API
    label = "IPinfo"
    description = "Looks up IP intelligence for one IP address."
    accepted_query_types = [QueryType.IP_ADDRESS]
    example_query = "8.8.8.8"
    example_location = "https://ipinfo.io"

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        if not is_valid_ipv4_address(query):
            return ProviderError(
                code=ErrorCode.BAD_QUERY_TYPE.value,
                message="IPinfo expects a string IP address.",
            )

        return None

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        settings = get_settings()
        if not settings.ipinfo_api_key:
            return self._build_demo_result(query)

        request_url = f"{self.source_config.location.rstrip('/')}/{quote(str(query))}/json"

        try:
            response = get_json(
                request_url,
                params={"token": settings.ipinfo_api_key},
                headers={"Accept": "application/json"},
                timeout_seconds=self.source_config.timeout_seconds,
            )
        except HTTPClientError as error:
            return self._build_live_error_result(error=error, mode="live")

        if not isinstance(response.data, dict):
            return self._build_bad_response_result(
                message="IPinfo returned a non-object JSON payload.",
                mode="live",
                response_code=response.status_code,
            )

        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": response.data,
            "metadata": {
                "response_code": response.status_code,
                "provider": "ipinfo",
                "mode": "live",
                "request_url": response.url,
            },
        }

    def _build_demo_result(self, query: Any) -> dict[str, Any]:
        """Return a readable fallback result when no live key is configured."""
        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": {
                "ip": query,
                "city": "Mountain View",
                "region": "California",
                "country": "US",
                "org": "AS15169 Google LLC",
            },
            "metadata": {
                "response_code": 200,
                "provider": "ipinfo",
                "mode": "demo",
            },
        }

    def _build_live_error_result(self, error: HTTPClientError, *, mode: str) -> dict[str, Any]:
        """Turn a live provider failure into the shared outer wrapper payload."""
        error_code = ErrorCode.PROVIDER_HTTP_ERROR
        if error.failure_kind == "timeout":
            error_code = ErrorCode.PROVIDER_TIMEOUT
        elif error.failure_kind == "network_error":
            error_code = ErrorCode.PROVIDER_NETWORK_ERROR
        elif error.failure_kind == "invalid_json":
            error_code = ErrorCode.PROVIDER_BAD_RESPONSE
        elif error.status_code == 429:
            error_code = ErrorCode.PROVIDER_RATE_LIMITED

        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=error_code.value,
                message=str(error),
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": error.status_code or 0,
            },
        }

    def _build_bad_response_result(
        self,
        *,
        message: str,
        mode: str,
        response_code: int,
    ) -> dict[str, Any]:
        """Return a shared payload for malformed provider data."""
        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=ErrorCode.PROVIDER_BAD_RESPONSE.value,
                message=message,
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": response_code,
            },
        }


class CrtShAdapter(BaseSourceAdapter):
    """Adapter for certificate search results."""

    provider = ProviderKind.CRT_SH
    source_kind = SourceKind.SCRAPER
    label = "crt.sh"
    description = "Looks up certificate transparency records for a domain."
    accepted_query_types = [QueryType.DOMAIN]
    example_query = "example.com"
    example_location = "https://crt.sh"

    def preview_response(self):  # type: ignore[override]
        """Return a stable example response without requiring a live network call."""
        return self._build_success_response(
            query=self.example_query,
            provider_result={
                "status": FetchStatus.SUCCESS,
                "raw_data": [
                    {
                        "common_name": "example.com",
                        "issuer_name": "Let's Encrypt",
                        "not_before": "2026-01-10T00:00:00Z",
                    }
                ],
                "metadata": {
                    "provider": self.provider.value,
                    "mode": "preview",
                    "response_code": 200,
                    "result_count": 1,
                },
            },
        )

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        error_message = get_crt_sh_query_error(query)
        if error_message is not None:
            return ProviderError(
                code=ErrorCode.BAD_QUERY_TYPE.value,
                message=error_message,
            )

        return None

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        request_url = self.source_config.location.rstrip("/")

        try:
            response = get_json(
                request_url,
                params={
                    "q": query,
                    "output": "json",
                },
                headers={"Accept": "application/json"},
                timeout_seconds=self.source_config.timeout_seconds,
            )
        except HTTPClientError as error:
            return self._build_live_error_result(error=error, mode="search")

        if not isinstance(response.data, list):
            return self._build_bad_response_result(
                message="crt.sh returned a non-list JSON payload.",
                mode="search",
                response_code=response.status_code,
            )

        if not response.data:
            return {
                "status": FetchStatus.NO_RESULTS,
                "raw_data": response.data,
                "metadata": {
                    "provider": self.provider.value,
                    "mode": "search",
                    "response_code": response.status_code,
                    "request_url": response.url,
                    "result_count": 0,
                },
            }

        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": response.data,
            "metadata": {
                "provider": self.provider.value,
                "mode": "search",
                "response_code": response.status_code,
                "request_url": response.url,
                "result_count": len(response.data),
            },
        }

    def _build_live_error_result(self, error: HTTPClientError, *, mode: str) -> dict[str, Any]:
        """Turn a live provider failure into the shared outer wrapper payload."""
        error_code = ErrorCode.PROVIDER_HTTP_ERROR
        if error.failure_kind == "timeout":
            error_code = ErrorCode.PROVIDER_TIMEOUT
        elif error.failure_kind == "network_error":
            error_code = ErrorCode.PROVIDER_NETWORK_ERROR
        elif error.failure_kind == "invalid_json":
            error_code = ErrorCode.PROVIDER_BAD_RESPONSE
        elif error.status_code == 429:
            error_code = ErrorCode.PROVIDER_RATE_LIMITED

        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=error_code.value,
                message=str(error),
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": error.status_code or 0,
            },
        }

    def _build_bad_response_result(
        self,
        *,
        message: str,
        mode: str,
        response_code: int,
    ) -> dict[str, Any]:
        """Return a shared payload for malformed provider data."""
        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=ErrorCode.PROVIDER_BAD_RESPONSE.value,
                message=message,
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": response_code,
            },
        }


class OpenSkyAdapter(BaseSourceAdapter):
    """Adapter for aircraft or bounding-box lookups."""

    provider = ProviderKind.OPENSKY
    source_kind = SourceKind.API
    label = "OpenSky"
    description = "Returns live aircraft state data for an aircraft id or bounding box."
    accepted_query_types = [QueryType.AIRCRAFT_ID, QueryType.BOUNDING_BOX]
    example_query = "AAL123"
    example_location = "https://opensky-network.org"

    def preview_response(self):  # type: ignore[override]
        """Return a stable example response without requiring a live network call."""
        return self._build_success_response(
            query=self.example_query,
            provider_result={
                "status": FetchStatus.SUCCESS,
                "raw_data": {
                    "time": 1_777_090_400,
                    "states": [
                        [
                            "abc123",
                            "AAL123",
                            "United States",
                            None,
                            None,
                            -86.1581,
                            39.7684,
                            11200.0,
                        ]
                    ],
                },
                "metadata": {
                    "provider": self.provider.value,
                    "mode": "preview",
                    "response_code": 200,
                    "state_count": 1,
                },
            },
        )

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        if is_valid_aircraft_id(query):
            return None

        if has_valid_bounding_box(query):
            return None

        return ProviderError(
            code=ErrorCode.BAD_QUERY_TYPE.value,
            message="OpenSky expects an aircraft id string or a bounding box with lamin, lamax, lomin, lomax.",
        )

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        request_url = f"{self.source_config.location.rstrip('/')}/api/states/all"
        if isinstance(query, dict):
            return self._fetch_bounding_box_states(query=query, request_url=request_url)

        return self._fetch_aircraft_states(query=query, request_url=request_url)

    def _fetch_bounding_box_states(self, *, query: dict[str, Any], request_url: str) -> dict[str, Any]:
        """Fetch OpenSky states for one bounding box."""
        try:
            response = get_json(
                request_url,
                params={
                    "lamin": query["lamin"],
                    "lamax": query["lamax"],
                    "lomin": query["lomin"],
                    "lomax": query["lomax"],
                },
                headers={"Accept": "application/json"},
                timeout_seconds=self.source_config.timeout_seconds,
            )
        except HTTPClientError as error:
            return self._build_live_error_result(error=error, mode="bounds")

        return self._build_live_result(response_data=response.data, response_code=response.status_code, request_url=response.url, mode="bounds")

    def _fetch_aircraft_states(self, *, query: str, request_url: str) -> dict[str, Any]:
        """Fetch OpenSky states for one aircraft-style lookup."""
        try:
            response = get_json(
                request_url,
                params={"icao24": str(query).strip().lower()},
                headers={"Accept": "application/json"},
                timeout_seconds=self.source_config.timeout_seconds,
            )
        except HTTPClientError as error:
            return self._build_live_error_result(error=error, mode="aircraft")

        return self._build_live_result(
            response_data=response.data,
            response_code=response.status_code,
            request_url=response.url,
            mode="aircraft",
        )

    def _build_live_result(
        self,
        *,
        response_data: Any,
        response_code: int,
        request_url: str,
        mode: str,
    ) -> dict[str, Any]:
        """Validate one live OpenSky payload and wrap it in the shared adapter shape."""
        if not isinstance(response_data, dict):
            return self._build_bad_response_result(
                message="OpenSky returned a non-object JSON payload.",
                mode=mode,
                response_code=response_code,
            )

        states = response_data.get("states")
        if states is None:
            return {
                "status": FetchStatus.NO_RESULTS,
                "raw_data": response_data,
                "metadata": {
                    "provider": self.provider.value,
                    "mode": mode,
                    "response_code": response_code,
                    "request_url": request_url,
                    "state_count": 0,
                },
            }

        if not isinstance(states, list):
            return self._build_bad_response_result(
                message="OpenSky returned a payload with a non-list states field.",
                mode=mode,
                response_code=response_code,
            )

        for state_vector in states:
            if not isinstance(state_vector, list):
                return self._build_bad_response_result(
                    message="OpenSky returned a states list with a non-list state vector.",
                    mode=mode,
                    response_code=response_code,
                )

        if not states:
            return {
                "status": FetchStatus.NO_RESULTS,
                "raw_data": response_data,
                "metadata": {
                    "provider": self.provider.value,
                    "mode": mode,
                    "response_code": response_code,
                    "request_url": request_url,
                    "state_count": 0,
                },
            }

        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": response_data,
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": response_code,
                "request_url": request_url,
                "state_count": len(states),
            },
        }

    def _build_live_error_result(self, error: HTTPClientError, *, mode: str) -> dict[str, Any]:
        """Turn a live provider failure into the shared outer wrapper payload."""
        error_code = ErrorCode.PROVIDER_HTTP_ERROR
        if error.failure_kind == "timeout":
            error_code = ErrorCode.PROVIDER_TIMEOUT
        elif error.failure_kind == "network_error":
            error_code = ErrorCode.PROVIDER_NETWORK_ERROR
        elif error.failure_kind == "invalid_json":
            error_code = ErrorCode.PROVIDER_BAD_RESPONSE
        elif error.status_code == 429:
            error_code = ErrorCode.PROVIDER_RATE_LIMITED

        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=error_code.value,
                message=str(error),
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": error.status_code or 0,
            },
        }

    def _build_bad_response_result(
        self,
        *,
        message: str,
        mode: str,
        response_code: int,
    ) -> dict[str, Any]:
        """Return a shared payload for malformed provider data."""
        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=ErrorCode.PROVIDER_BAD_RESPONSE.value,
                message=message,
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": response_code,
            },
        }


class NominatimAdapter(BaseSourceAdapter):
    """Adapter for forward and reverse geocoding."""

    provider = ProviderKind.NOMINATIM
    source_kind = SourceKind.API
    label = "Nominatim"
    description = "Geocodes a place name or reverse-geocodes coordinates."
    accepted_query_types = [QueryType.COORDINATES, QueryType.PLACE_NAME]
    example_query = "Indianapolis"
    example_location = "https://nominatim.openstreetmap.org"

    def preview_response(self):  # type: ignore[override]
        """Return a stable example response without requiring a live network call."""
        return self._build_success_response(
            query=self.example_query,
            provider_result={
                "status": FetchStatus.SUCCESS,
                "raw_data": [
                    {
                        "display_name": "Indianapolis, Marion County, Indiana, United States",
                        "lat": "39.7684",
                        "lon": "-86.1581",
                    }
                ],
                "metadata": {
                    "provider": self.provider.value,
                    "mode": "preview",
                    "response_code": 200,
                },
            },
        )

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        if is_valid_place_name(query):
            return None

        if has_valid_coordinates(query):
            return None

        return ProviderError(
            code=ErrorCode.BAD_QUERY_TYPE.value,
            message="Nominatim expects a place name string or coordinates with lat and lon.",
        )

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        if isinstance(query, dict):
            return self._fetch_reverse_geocode(query)

        return self._fetch_search_results(query)

    def _fetch_reverse_geocode(self, query: dict[str, Any]) -> dict[str, Any]:
        """Fetch one live reverse-geocode result from Nominatim."""
        request_url = f"{self.source_config.location.rstrip('/')}/reverse"

        try:
            response = get_json(
                request_url,
                params={
                    "format": "jsonv2",
                    "lat": query["lat"],
                    "lon": query["lon"],
                },
                headers={"Accept": "application/json"},
                timeout_seconds=self.source_config.timeout_seconds,
            )
        except HTTPClientError as error:
            return self._build_live_error_result(error=error, mode="reverse")

        if not isinstance(response.data, dict):
            return self._build_bad_response_result(
                message="Nominatim reverse geocode returned a non-object JSON payload.",
                mode="reverse",
                response_code=response.status_code,
            )

        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": response.data,
            "metadata": {
                "provider": self.provider.value,
                "mode": "reverse",
                "response_code": response.status_code,
                "request_url": response.url,
            },
        }

    def _fetch_search_results(self, query: str) -> dict[str, Any]:
        """Fetch live forward-geocode search results from Nominatim."""
        request_url = f"{self.source_config.location.rstrip('/')}/search"

        try:
            response = get_json(
                request_url,
                params={
                    "format": "jsonv2",
                    "q": query,
                },
                headers={"Accept": "application/json"},
                timeout_seconds=self.source_config.timeout_seconds,
            )
        except HTTPClientError as error:
            return self._build_live_error_result(error=error, mode="search")

        if not isinstance(response.data, list):
            return self._build_bad_response_result(
                message="Nominatim search returned a non-list JSON payload.",
                mode="search",
                response_code=response.status_code,
            )

        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": response.data,
            "metadata": {
                "provider": self.provider.value,
                "mode": "search",
                "response_code": response.status_code,
                "request_url": response.url,
            },
        }

    def _build_live_error_result(self, error: HTTPClientError, *, mode: str) -> dict[str, Any]:
        """Turn a live provider failure into the shared outer wrapper payload."""
        error_code = ErrorCode.PROVIDER_HTTP_ERROR
        if error.failure_kind == "timeout":
            error_code = ErrorCode.PROVIDER_TIMEOUT
        elif error.failure_kind == "network_error":
            error_code = ErrorCode.PROVIDER_NETWORK_ERROR
        elif error.failure_kind == "invalid_json":
            error_code = ErrorCode.PROVIDER_BAD_RESPONSE
        elif error.status_code == 429:
            error_code = ErrorCode.PROVIDER_RATE_LIMITED

        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=error_code.value,
                message=str(error),
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": error.status_code or 0,
            },
        }

    def _build_bad_response_result(
        self,
        *,
        message: str,
        mode: str,
        response_code: int,
    ) -> dict[str, Any]:
        """Return a shared payload for malformed provider data."""
        return {
            "status": FetchStatus.ERROR,
            "raw_data": None,
            "error": ProviderError(
                code=ErrorCode.PROVIDER_BAD_RESPONSE.value,
                message=message,
            ),
            "metadata": {
                "provider": self.provider.value,
                "mode": mode,
                "response_code": response_code,
            },
        }
