"""Schemas for saved raw provider records."""

from __future__ import annotations

from typing import Any

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind
from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class SavedRawRecord(BaseModel):
    """One raw provider response saved to local storage."""

    record_id: str = Field(default="", description="Stable id for one saved raw record")
    case_id: str = Field(default="default", description="Investigation case id")
    source_id: str = Field(default="", description="Which source config produced the record")
    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Which provider answered")
    source_type: SourceKind = Field(default=SourceKind.API, description="Which source family answered")
    query: Any = Field(default="", description="What was asked")
    fetched_at: str = Field(default="", description="When the provider data was fetched")
    saved_at: str = Field(default="", description="When the raw record was saved locally")
    status: FetchStatus = Field(default=FetchStatus.SUCCESS, description="Result status")
    raw_data: Any = Field(default=None, description="Original provider payload")
    error: ProviderError | None = Field(default=None, description="Provider error details if the fetch failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra fetch details from the provider")
