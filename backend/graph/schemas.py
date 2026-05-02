"""Schemas for graph database writes."""

from __future__ import annotations

from typing import Any

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind
from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class GraphNode(BaseModel):
    """One node ready to be written into the graph database."""

    entity_key: str = Field(default="", description="Stable unique key for this node")
    entity_type: str = Field(default="", description="Readable node type like person, domain, or ip")
    canonical_value: str = Field(default="", description="Stable comparable value for this node")
    display_value: str = Field(default="", description="Human-readable node label")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra source facts for this node")


class GraphRelationship(BaseModel):
    """One edge ready to be written into the graph database."""

    relationship_key: str = Field(default="", description="Stable unique key for this edge")
    relationship_type: str = Field(default="", description="Readable edge label")
    from_entity_key: str = Field(default="", description="Source node key")
    to_entity_key: str = Field(default="", description="Target node key")
    confidence_percent: int = Field(default=0, description="How confident this edge is")
    evidence_record_id: str = Field(default="", description="Which record supports this edge")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra source facts for this edge")


class GraphSnapshot(BaseModel):
    """A read-side snapshot of graph nodes and relationships."""

    nodes: list[GraphNode] = Field(default_factory=list, description="Graph nodes")
    relationships: list[GraphRelationship] = Field(default_factory=list, description="Graph relationships")


class GraphWriteResult(BaseModel):
    """The result of writing one record's graph artifacts."""

    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Which provider created the source record")
    source_type: SourceKind = Field(default=SourceKind.API, description="Which source family created the source record")
    raw_record_id: str = Field(default="", description="Which record was being written")
    query: Any = Field(default="", description="Original source query")
    status: FetchStatus = Field(default=FetchStatus.SUCCESS, description="Graph write status")
    error: ProviderError | None = Field(default=None, description="Why graph writing failed, if it failed")
    nodes_written: int = Field(default=0, description="How many unique nodes were written")
    relationships_written: int = Field(default=0, description="How many unique edges were written")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra graph write notes")
