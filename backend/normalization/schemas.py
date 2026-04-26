"""Schemas for normalized provider records."""

from __future__ import annotations

from typing import Any

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind
from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class NormalizedRecord(BaseModel):
    """One saved raw record converted into the shared normalized shape."""

    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Which provider the raw record came from")
    source_type: SourceKind = Field(default=SourceKind.API, description="Which source family created the raw record")
    raw_record_id: str = Field(default="", description="Saved raw record id")
    query: Any = Field(default="", description="Original query that led to the raw record")
    status: FetchStatus = Field(default=FetchStatus.SUCCESS, description="Normalization status")
    error: ProviderError | None = Field(default=None, description="Normalization or provider error details")
    normalized_data: Any = Field(default=None, description="Shared normalized output")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra normalization notes")
