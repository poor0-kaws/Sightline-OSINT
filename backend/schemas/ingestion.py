"""Schemas for the data source architecture layer."""

from enum import Enum
from typing import Any

from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class SourceKind(str, Enum):
    """High-level source families."""

    API = "api"
    SCRAPER = "scraper"
    WEBHOOK = "webhook"
    CSV = "csv"
    MANUAL = "manual"


class ProviderKind(str, Enum):
    """Concrete providers from the architecture note."""

    IPINFO = "ipinfo"
    CRT_SH = "crt.sh"
    OPENSKY = "opensky"
    NOMINATIM = "nominatim"
    WEBHOOK = "webhook"
    CSV_UPLOAD = "csv_upload"
    MANUAL_INPUT = "manual_input"


class QueryType(str, Enum):
    """Kinds of input a provider can accept."""

    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    AIRCRAFT_ID = "aircraft_id"
    BOUNDING_BOX = "bounding_box"
    COORDINATES = "coordinates"
    PLACE_NAME = "place_name"
    PAYLOAD_BODY = "payload_body"
    FILE_ROWS = "file_rows"
    MANUAL_FIELDS = "manual_fields"


class FetchStatus(str, Enum):
    """Status values for the raw provider wrapper."""

    SUCCESS = "success"
    NO_RESULTS = "no_results"
    PARTIAL_SUCCESS = "partial_success"
    ERROR = "error"


class SourceConfig(BaseModel):
    """Configuration for one source adapter."""

    source_id: str = Field(default="source-demo", description="Stable source id")
    case_id: str = Field(default="default", description="Investigation case id")
    source_kind: SourceKind = Field(default=SourceKind.API, description="High-level source family")
    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Concrete provider")
    location: str = Field(default="", description="Base URL, topic, or file hint")
    display_name: str = Field(default="", description="Human-readable source name")
    timeout_seconds: int = Field(default=30, description="Simple timeout hint")


class SourceRequest(BaseModel):
    """Input to a source adapter."""

    source: SourceConfig = Field(default_factory=SourceConfig)
    query: Any = Field(default="", description="Provider input like an IP, domain, payload, or rows")


class ProviderDefinition(BaseModel):
    """Human-friendly description of a provider."""

    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Provider key")
    source_kind: SourceKind = Field(default=SourceKind.API, description="Source family")
    label: str = Field(default="IPinfo", description="Visible provider name")
    description: str = Field(default="Looks up IP intelligence", description="What the provider does")
    accepted_query_types: list[QueryType] = Field(default_factory=list, description="Supported input kinds")
    example_query: Any = Field(default="8.8.8.8", description="Example input")
    example_location: str = Field(default="https://ipinfo.io", description="Example source location")


class ProviderError(BaseModel):
    """Simple provider-level error details."""

    code: str = Field(default="unknown_error", description="Short machine-friendly code")
    message: str = Field(default="Unknown error", description="Human-readable error message")


class RawProviderResponse(BaseModel):
    """Shared outer wrapper for every raw provider response."""

    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Which provider answered")
    source_type: SourceKind = Field(default=SourceKind.API, description="Which source family answered")
    query: Any = Field(default="", description="What the adapter was asked to fetch")
    fetched_at: str = Field(default="", description="When the data was fetched")
    status: FetchStatus = Field(default=FetchStatus.SUCCESS, description="Result status")
    raw_data: Any = Field(default=None, description="Original provider payload")
    error: ProviderError | None = Field(default=None, description="Provider error details if the fetch failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra fetch details like response code")
