"""Schemas for ingestion jobs and source definitions."""

# `Enum` gives named choices for source kinds.
from enum import Enum

# `Field` lets us add simple defaults and descriptions.
from backend.utils.optional_deps import Field
# `BaseModel` gives us a structured data container.
from backend.utils.optional_deps import BaseModel


class SourceKind(str, Enum):
    """Supported ingestion source types."""

    API = "api"
    CSV = "csv"
    SCRAPER = "scraper"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class IngestionSourceConfig(BaseModel):
    """Basic source definition sent into ingestion jobs."""

    source_id: str = Field(default="source-demo", description="Stable source name")
    source_kind: SourceKind = Field(default=SourceKind.API, description="Connector type")
    location: str = Field(default="TODO", description="URL, file path, or webhook topic")
    display_name: str = Field(default="Demo Source", description="Human-readable source name")


class SourceDefinition(BaseModel):
    """Human-friendly description of one supported source family."""

    source_kind: SourceKind = Field(default=SourceKind.API, description="Stable source family key")
    label: str = Field(default="API", description="Visible source label")
    description: str = Field(default="Pulls JSON records from a remote API", description="What this source does")
    example_location: str = Field(default="https://api.example.test/search", description="Example location value")
    raw_shape_summary: str = Field(default="JSON response body", description="What the raw data looks like")


class SourcePreview(BaseModel):
    """Tiny example of the raw data a source can emit."""

    source_kind: SourceKind = Field(default=SourceKind.API, description="Which source family this preview belongs to")
    source_id: str = Field(default="api-demo", description="Example source identifier")
    raw_records: list[dict] = Field(default_factory=list, description="Example raw records before normalization")
    note: str = Field(default="Preview only", description="Short human explanation")


class IngestionJobCreate(BaseModel):
    """Request body for creating an ingestion job."""

    source: IngestionSourceConfig = Field(default_factory=IngestionSourceConfig)


class IngestionJobStatus(BaseModel):
    """Response model for a queued ingestion job."""

    job_id: str = Field(default="job-demo", description="Queued job identifier")
    status: str = Field(default="queued", description="Current job state")
    note: str = Field(default="TODO [CORE]: run connector and normalize records", description="What happens next")
