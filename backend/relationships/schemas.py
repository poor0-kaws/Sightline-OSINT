"""Schemas for graph-ready relationship extraction results."""

from __future__ import annotations

from enum import Enum
from typing import Any

from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceKind
from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class EntityType(str, Enum):
    """Small set of graph node kinds used by the first extractor."""

    PERSON = "person"
    EMAIL = "email"
    PHONE = "phone"
    COMPANY = "company"
    IP = "ip"
    LOCATION = "location"
    ORGANIZATION = "organization"
    CERTIFICATE = "certificate"
    DOMAIN = "domain"
    ISSUER = "issuer"


class RelationshipType(str, Enum):
    """Relationship labels the graph layer can write directly later."""

    PERSON_USES_EMAIL = "person_uses_email"
    PERSON_USES_PHONE = "person_uses_phone"
    PERSON_ASSOCIATED_WITH_COMPANY = "person_associated_with_company"
    IP_BELONGS_TO_ORGANIZATION = "ip_belongs_to_organization"
    IP_LOCATED_IN = "ip_located_in"
    CERTIFICATE_MENTIONS_DOMAIN = "certificate_mentions_domain"
    CERTIFICATE_ISSUED_BY = "certificate_issued_by"


class EntityReference(BaseModel):
    """A graph-ready pointer to one entity."""

    entity_id: str = Field(default="", description="Stable local id for this entity reference")
    entity_type: EntityType = Field(default=EntityType.PERSON, description="What kind of entity this is")
    canonical_value: str = Field(default="", description="Stable comparison value")
    display_value: str = Field(default="", description="Human-readable label")


class ExtractedRelationship(BaseModel):
    """One graph-ready relationship with evidence and confidence."""

    relationship_id: str = Field(default="", description="Stable local id for this relationship")
    relationship_type: RelationshipType = Field(
        default=RelationshipType.PERSON_USES_EMAIL,
        description="What connection exists between the two entities",
    )
    from_entity: EntityReference = Field(default_factory=EntityReference)
    to_entity: EntityReference = Field(default_factory=EntityReference)
    confidence_percent: int = Field(default=0, description="How confident this explicit edge is")
    evidence_record_id: str = Field(default="", description="Which normalized/raw record supports this edge")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra relationship details")


class RelationshipExtractionResult(BaseModel):
    """All relationships extracted from one normalized record."""

    provider: ProviderKind = Field(default=ProviderKind.IPINFO, description="Which provider created the source record")
    source_type: SourceKind = Field(default=SourceKind.API, description="Which source family created the source record")
    raw_record_id: str = Field(default="", description="The normalized/raw record id being processed")
    query: Any = Field(default="", description="The original upstream query")
    status: FetchStatus = Field(default=FetchStatus.SUCCESS, description="Extraction status")
    error: ProviderError | None = Field(default=None, description="Why extraction failed, if it failed")
    relationships: list[ExtractedRelationship] = Field(default_factory=list, description="Graph-ready edges")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra extraction notes")
