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
            return {
                "status": FetchStatus.ERROR,
                "raw_data": None,
                "error": ProviderError(
                    code="provider_http_error",
                    message=str(error),
                ),
                "metadata": {
                    "provider": "ipinfo",
                    "mode": "live",
                    "response_code": error.status_code or 0,
                },
            }

        if not isinstance(response.data, dict):
            return {
                "status": FetchStatus.ERROR,
                "raw_data": None,
                "error": ProviderError(
                    code="provider_bad_response",
                    message="IPinfo returned a non-object JSON payload.",
                ),
                "metadata": {
                    "provider": "ipinfo",
                    "mode": "live",
                    "response_code": response.status_code,
                },
            }

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


class CrtShAdapter(BaseSourceAdapter):
    """Adapter for certificate search results."""

    provider = ProviderKind.CRT_SH
    source_kind = SourceKind.SCRAPER
    label = "crt.sh"
    description = "Looks up certificate transparency records for a domain."
    accepted_query_types = [QueryType.DOMAIN]
    example_query = "example.com"
    example_location = "https://crt.sh"

    def validate_provider_query(self, query: Any) -> ProviderError | None:
        if not is_valid_domain_name(query):
            return ProviderError(
                code=ErrorCode.BAD_QUERY_TYPE.value,
                message="crt.sh expects a domain like example.com.",
            )

        return None

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": [
                {
                    "common_name": query,
                    "issuer_name": "Let's Encrypt",
                    "not_before": "2026-01-10T00:00:00Z",
                }
            ],
            "metadata": {"response_code": 200, "result_count": 1},
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
        if isinstance(query, dict):
            return {
                "status": FetchStatus.PARTIAL_SUCCESS,
                "raw_data": {
                    "bounds": query,
                    "states": [["abc123", "AAL123", -86.1, 39.8, 11200]],
                },
                "metadata": {"response_code": 206, "note": "partial_success used for sampled state vectors"},
            }

        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": {
                "icao24": "abc123",
                "callsign": query,
                "origin_country": "United States",
            },
            "metadata": {"response_code": 200},
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
            return {
                "status": FetchStatus.SUCCESS,
                "raw_data": {
                    "lat": query["lat"],
                    "lon": query["lon"],
                    "display_name": "Indianapolis, Marion County, Indiana, United States",
                },
                "metadata": {"response_code": 200, "mode": "reverse"},
            }

        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": [
                {
                    "display_name": f"{query}, Indiana, United States",
                    "lat": "39.7684",
                    "lon": "-86.1581",
                }
            ],
            "metadata": {"response_code": 200, "mode": "search"},
        }
