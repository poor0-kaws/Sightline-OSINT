"""Rule-based resolution helpers."""

from backend.resolution.candidates import build_domain_candidate
from backend.resolution.candidates import build_ip_candidate
from backend.resolution.candidates import build_match_candidates_from_normalized_record
from backend.resolution.candidates import build_person_candidate
from backend.resolution.engine import resolve_match_candidates
from backend.resolution.engine import resolve_person_records
from backend.resolution.schemas import EntityType
from backend.resolution.schemas import MatchCandidate
from backend.resolution.schemas import MatchReason
from backend.resolution.schemas import PersonRecord
from backend.resolution.schemas import ResolutionDecision
from backend.resolution.schemas import ResolutionResult

__all__ = [
    "EntityType",
    "MatchCandidate",
    "MatchReason",
    "PersonRecord",
    "ResolutionDecision",
    "ResolutionResult",
    "build_domain_candidate",
    "build_ip_candidate",
    "build_match_candidates_from_normalized_record",
    "build_person_candidate",
    "resolve_match_candidates",
    "resolve_person_records",
]
