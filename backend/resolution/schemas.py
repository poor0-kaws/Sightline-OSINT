"""Schemas for rule-based entity resolution."""

from __future__ import annotations

from enum import Enum
from typing import Any

from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class ResolutionDecision(str, Enum):
    """Possible outcomes for one entity-record comparison."""

    MERGE = "merge"
    REVIEW_NEEDED = "review_needed"
    NO_MATCH = "no_match"


class EntityType(str, Enum):
    """High-level kinds of entities the resolution layer can compare."""

    PERSON = "person"
    DOMAIN = "domain"
    IP = "ip"


class PersonRecord(BaseModel):
    """A normalized person-like record used by the resolution engine."""

    record_id: str = Field(default="", description="Stable id for this person-like record")
    full_name: str = Field(default="", description="Person full name")
    emails: list[str] = Field(default_factory=list, description="Known email addresses for the person")
    phone_numbers: list[str] = Field(default_factory=list, description="Known phone numbers for the person")
    company_name: str = Field(default="", description="Associated company name")
    city: str = Field(default="", description="Associated city")
    region: str = Field(default="", description="Associated region or state")
    country: str = Field(default="", description="Associated country")


class MatchCandidate(BaseModel):
    """A general comparable record that can be routed to the right resolver."""

    record_id: str = Field(default="", description="Stable id for this candidate")
    entity_type: EntityType = Field(default=EntityType.PERSON, description="What kind of entity this candidate represents")
    canonical_value: str = Field(default="", description="Main exact-match value for simple entity types")
    display_value: str = Field(default="", description="Human-readable value for logs and debugging")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Extra typed fields for richer entity comparisons")


class MatchReason(BaseModel):
    """One scoring reason that increased confidence."""

    helper_name: str = Field(default="", description="Which helper awarded the points")
    confidence_added: int = Field(default=0, description="How many confidence points were added")
    message: str = Field(default="", description="Why the confidence increase was earned")


class ResolutionResult(BaseModel):
    """The final resolution result for one pair of person-like records."""

    left_record_id: str = Field(default="", description="Left-side record id")
    right_record_id: str = Field(default="", description="Right-side record id")
    confidence_percent: int = Field(default=0, description="Final confidence score from 0 to 100")
    decision: ResolutionDecision = Field(default=ResolutionDecision.NO_MATCH, description="Resolution outcome")
    reasons: list[MatchReason] = Field(default_factory=list, description="Scoring reasons that raised confidence")


class ResolutionBatchResult(BaseModel):
    """Resolution output for many saved records at once."""

    status: str = Field(default="success", description="Batch status")
    source_record_count: int = Field(default=0, description="How many normalized records were scanned")
    candidate_count: int = Field(default=0, description="How many comparable candidates were found")
    comparison_count: int = Field(default=0, description="How many candidate pairs were compared")
    candidates: list[MatchCandidate] = Field(
        default_factory=list,
        description="Comparable entities found in the records",
    )
    matches: list[ResolutionResult] = Field(default_factory=list, description="Pairwise resolution decisions")
    summary: dict[str, int] = Field(default_factory=dict, description="Counts by decision")
