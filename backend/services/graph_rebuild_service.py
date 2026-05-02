"""Rebuild graph storage from saved raw records."""

from __future__ import annotations

from typing import Any

from backend.graph import GraphWriteService
from backend.normalization import normalize_saved_raw_record
from backend.relationships import extract_relationships_from_normalized_record
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord


def rebuild_graph_from_saved_raw_records(
    *,
    saved_raw_records: list[SavedRawRecord],
    graph_write_service: GraphWriteService,
) -> dict[str, Any]:
    """Replay saved raw records through normalize -> relationships -> graph write."""
    write_results = []

    for saved_raw_record in saved_raw_records:
        normalized_record = normalize_saved_raw_record(saved_raw_record)
        relationship_result = extract_relationships_from_normalized_record(normalized_record)
        write_results.append(graph_write_service.write_graph_artifacts(normalized_record, relationship_result))

    return _build_rebuild_summary(
        saved_raw_record_count=len(saved_raw_records),
        write_results=write_results,
    )


def _build_rebuild_summary(*, saved_raw_record_count: int, write_results: list[object]) -> dict[str, Any]:
    """Build one small JSON-friendly rebuild summary."""
    status_counts = {
        FetchStatus.SUCCESS.value: 0,
        FetchStatus.NO_RESULTS.value: 0,
        FetchStatus.ERROR.value: 0,
    }
    nodes_written = 0
    relationships_written = 0

    for write_result in write_results:
        status = getattr(getattr(write_result, "status", None), "value", "")
        if status not in status_counts:
            status_counts[status] = 0

        status_counts[status] += 1
        nodes_written += int(getattr(write_result, "nodes_written", 0) or 0)
        relationships_written += int(getattr(write_result, "relationships_written", 0) or 0)

    return {
        "status": "success" if status_counts[FetchStatus.ERROR.value] == 0 else "partial",
        "saved_raw_record_count": saved_raw_record_count,
        "write_count": len(write_results),
        "nodes_written": nodes_written,
        "relationships_written": relationships_written,
        "status_counts": status_counts,
        "writes": write_results,
    }
