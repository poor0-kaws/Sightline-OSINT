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


class IngestionSourceConfig(BaseModel):
    """Basic source definition sent into ingestion jobs."""

    source_id: str = Field(default="source-demo", description="Stable source name")
    source_kind: SourceKind = Field(default=SourceKind.API, description="Connector type")
    location: str = Field(default="TODO", description="URL, file path, or webhook topic")


class IngestionJobCreate(BaseModel):
    """Request body for creating an ingestion job."""

    source: IngestionSourceConfig = Field(default_factory=IngestionSourceConfig)


class IngestionJobStatus(BaseModel):
    """Response model for a queued ingestion job."""

    job_id: str = Field(default="job-demo", description="Queued job identifier")
    status: str = Field(default="queued", description="Current job state")
    note: str = Field(default="TODO [CORE]: run connector and normalize records", description="What happens next")

