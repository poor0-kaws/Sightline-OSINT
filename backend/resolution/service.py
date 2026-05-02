"""Batch service that resolves entities across saved raw records."""

from __future__ import annotations

from backend.normalization import normalize_saved_raw_record
from backend.normalization.schemas import NormalizedRecord
from backend.resolution.candidates import build_match_candidates_from_normalized_record
from backend.resolution.engine import resolve_match_candidates
from backend.resolution.schemas import MatchCandidate
from backend.resolution.schemas import ResolutionBatchResult
from backend.resolution.schemas import ResolutionDecision
from backend.resolution.schemas import ResolutionResult
from backend.schemas.storage import SavedRawRecord


def resolve_saved_raw_records(saved_raw_records: list[SavedRawRecord]) -> ResolutionBatchResult:
    """Normalize saved records, build candidates, and compare them."""
    normalized_records = [
        normalize_saved_raw_record(saved_raw_record)
        for saved_raw_record in saved_raw_records
    ]
    return resolve_normalized_records(normalized_records)


def resolve_normalized_records(normalized_records: list[NormalizedRecord]) -> ResolutionBatchResult:
    """Resolve entities from already-normalized records."""
    candidates: list[MatchCandidate] = []

    for normalized_record in normalized_records:
        candidates.extend(build_match_candidates_from_normalized_record(normalized_record))

    return resolve_match_candidate_batch(
        candidates,
        source_record_count=len(normalized_records),
    )


def resolve_match_candidate_batch(
    candidates: list[MatchCandidate],
    *,
    source_record_count: int = 0,
) -> ResolutionBatchResult:
    """Compare candidates of the same type across different raw records."""
    comparable_candidates = _sort_candidates(candidates)
    matches: list[ResolutionResult] = []

    for left_index, left_candidate in enumerate(comparable_candidates):
        for right_candidate in comparable_candidates[left_index + 1:]:
            if left_candidate.entity_type != right_candidate.entity_type:
                continue

            if _record_root(left_candidate.record_id) == _record_root(right_candidate.record_id):
                continue

            matches.append(resolve_match_candidates(left_candidate, right_candidate))

    summary = _build_summary(matches)

    return ResolutionBatchResult(
        status="success",
        source_record_count=source_record_count,
        candidate_count=len(comparable_candidates),
        comparison_count=len(matches),
        candidates=comparable_candidates,
        matches=matches,
        summary=summary,
    )


def _sort_candidates(candidates: list[MatchCandidate]) -> list[MatchCandidate]:
    """Return a stable candidate order for repeatable API output."""
    return sorted(
        candidates,
        key=lambda candidate: (
            _entity_type_text(candidate.entity_type),
            candidate.canonical_value,
            candidate.record_id,
        ),
    )


def _build_summary(matches: list[ResolutionResult]) -> dict[str, int]:
    """Count match decisions for the API summary."""
    summary = {
        ResolutionDecision.MERGE.value: 0,
        ResolutionDecision.REVIEW_NEEDED.value: 0,
        ResolutionDecision.NO_MATCH.value: 0,
    }

    for match in matches:
        decision = match.decision.value if hasattr(match.decision, "value") else str(match.decision)
        if decision not in summary:
            summary[decision] = 0

        summary[decision] += 1

    return summary


def _record_root(record_id: str) -> str:
    """Return the saved raw record part of a candidate id."""
    if not isinstance(record_id, str):
        return ""

    return record_id.split(":", maxsplit=1)[0].strip()


def _entity_type_text(value: object) -> str:
    """Return a safe entity-type string for sorting."""
    if hasattr(value, "value"):
        value = value.value

    if not isinstance(value, str):
        return ""

    return value.strip()
