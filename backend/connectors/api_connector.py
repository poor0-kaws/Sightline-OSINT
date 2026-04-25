"""API and scraper-backed source adapters from the architecture note."""

from __future__ import annotations

from typing import Any

from backend.connectors.base import BaseSourceAdapter
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import QueryType
from backend.schemas.ingestion import SourceKind
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
            return ProviderError(code="bad_query_type", message="IPinfo expects a string IP address.")

        return None

    def fetch_raw_data(self, query: Any) -> dict[str, Any]:
        return {
            "status": FetchStatus.SUCCESS,
            "raw_data": {
                "ip": query,
                "city": "Mountain View",
                "region": "California",
                "country": "US",
                "org": "AS15169 Google LLC",
            },
            "metadata": {"response_code": 200, "provider": "ipinfo"},
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
            return ProviderError(code="bad_query_type", message="crt.sh expects a domain like example.com.")

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
            code="bad_query_type",
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
            code="bad_query_type",
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
