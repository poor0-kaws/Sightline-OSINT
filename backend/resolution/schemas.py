"""Schemas for rule-based person record resolution."""

from __future__ import annotations

from enum import Enum

from backend.utils.optional_deps import BaseModel
from backend.utils.optional_deps import Field


class ResolutionDecision(str, Enum):
    """Possible outcomes for one person-record comparison."""

    MERGE = "merge"
    REVIEW_NEEDED = "review_needed"
    NO_MATCH = "no_match"


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
