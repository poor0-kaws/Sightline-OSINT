"""Schemas for investigation cases."""

from __future__ import annotations

from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class CaseSummary(BaseModel):
    """Small case summary built from saved raw records."""

    case_id: str = Field(default="default", description="Investigation case id")
    record_count: int = Field(default=0, description="How many raw records belong to the case")
    provider_count: int = Field(default=0, description="How many providers appear in the case")
    latest_saved_at: str = Field(default="", description="Most recent saved raw record timestamp")
