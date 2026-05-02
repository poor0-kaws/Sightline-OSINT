"""Helpers for deriving case summaries from raw records."""

from __future__ import annotations

from backend.cases.schemas import CaseSummary
from backend.schemas.storage import SavedRawRecord


def build_case_summaries(saved_raw_records: list[SavedRawRecord]) -> list[CaseSummary]:
    """Group saved raw records by case id."""
    records_by_case: dict[str, list[SavedRawRecord]] = {}

    for saved_raw_record in saved_raw_records:
        case_id = saved_raw_record.case_id.strip() if saved_raw_record.case_id else "default"
        records_by_case.setdefault(case_id, []).append(saved_raw_record)

    summaries: list[CaseSummary] = []
    for case_id, records in sorted(records_by_case.items()):
        provider_values = {
            record.provider.value if hasattr(record.provider, "value") else str(record.provider)
            for record in records
        }
        summaries.append(
            CaseSummary(
                case_id=case_id,
                record_count=len(records),
                provider_count=len(provider_values),
                latest_saved_at=max((record.saved_at for record in records), default=""),
            )
        )

    if not summaries:
        return [CaseSummary()]

    return summaries
