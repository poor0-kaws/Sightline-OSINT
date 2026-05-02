"""Schemas for normalized provider records."""

from __future__ import annotations

from typing import Any

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind
from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class NormalizedEntity(BaseModel):
    """One shared entity extracted from provider-specific normalized data."""

    entity_type: str = Field(default="", description="What kind of real-world thing this is")
    canonical_value: str = Field(default="", description="Stable comparable value for this entity")
    display_value: str = Field(default="", description="Human-readable value for this entity")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra typed facts about the entity")


class NormalizedEvidence(BaseModel):
    """One traceable piece of support for an extracted entity."""

    evidence_type: str = Field(default="", description="Short label for the kind of supporting evidence")
    entity_type: str = Field(default="", description="Which entity type this evidence supports")
    canonical_value: str = Field(default="", description="Which entity value this evidence supports")
    detail: str = Field(default="", description="Human-readable explanation of the evidence")
    source_provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Which provider produced this evidence")
    source_record_id: str = Field(default="", description="Which saved raw record this evidence came from")
    source_query: Any = Field(default="", description="Which query produced the evidence")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra provider-specific evidence notes")


class NormalizedRelationshipCandidate(BaseModel):
    """One possible graph edge extracted from normalized data."""

    relationship_type: str = Field(default="", description="The possible edge label")
    source_entity_type: str = Field(default="", description="Left-side entity type")
    source_canonical_value: str = Field(default="", description="Left-side entity canonical value")
    target_entity_type: str = Field(default="", description="Right-side entity type")
    target_canonical_value: str = Field(default="", description="Right-side entity canonical value")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra relationship notes")


class NormalizedRecord(BaseModel):
    """One saved raw record converted into the shared normalized shape."""

    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Which provider the raw record came from")
    source_type: SourceKind = Field(default=SourceKind.API, description="Which source family created the raw record")
    case_id: str = Field(default="default", description="Investigation case id")
    raw_record_id: str = Field(default="", description="Saved raw record id")
    query: Any = Field(default="", description="Original query that led to the raw record")
    status: FetchStatus = Field(default=FetchStatus.SUCCESS, description="Normalization status")
    error: ProviderError | None = Field(default=None, description="Normalization or provider error details")
    normalized_data: Any = Field(default=None, description="Shared normalized output")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra normalization notes")
    entities: list[NormalizedEntity] = Field(default_factory=list, description="Shared extracted entities")
    evidence: list[NormalizedEvidence] = Field(default_factory=list, description="Traceable evidence for extracted entities")
    relationship_candidates: list[NormalizedRelationshipCandidate] = Field(
        default_factory=list,
        description="Possible graph edges extracted from the normalized data",
    )
