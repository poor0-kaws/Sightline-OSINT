"""Build frontend graph workspace payloads from real saved backend data."""

from __future__ import annotations

import math
from typing import Any

from backend.graph import GraphNode
from backend.graph import GraphRelationship
from backend.graph import GraphSnapshot
from backend.graph import GraphWriteService
from backend.graph import InMemoryGraphRepository
from backend.normalization import normalize_saved_raw_record
from backend.relationships import extract_relationships_from_normalized_record
from backend.schemas.ingestion import FetchStatus
from backend.schemas.storage import SavedRawRecord
from backend.settings import Settings


ENTITY_COLORS = {
    "person": "#d0b36a",
    "email": "#8fc3bb",
    "phone": "#8fc3bb",
    "organization": "#6ec5b8",
    "domain": "#7a9fb8",
    "ip": "#7a9fb8",
    "certificate": "#7a9fb8",
    "issuer": "#6ec5b8",
    "place": "#c76c57",
    "location": "#c76c57",
    "aircraft": "#b48fd8",
}

ENTITY_TIERS = {
    "person": "Identity",
    "email": "Contact",
    "phone": "Contact",
    "organization": "Entity",
    "domain": "Infrastructure",
    "ip": "Infrastructure",
    "certificate": "Infrastructure",
    "issuer": "Entity",
    "place": "Geospatial",
    "location": "Geospatial",
    "aircraft": "Aviation",
}


def build_graph_workspace_payload(
    *,
    settings: Settings,
    saved_raw_records: list[SavedRawRecord],
) -> dict[str, Any]:
    """Turn saved raw records into the graph payload consumed by the React app."""
    repository = InMemoryGraphRepository()
    graph_writer = GraphWriteService(repository)
    write_results = []

    for saved_raw_record in saved_raw_records:
        normalized_record = normalize_saved_raw_record(saved_raw_record)
        relationship_result = extract_relationships_from_normalized_record(normalized_record)
        write_result = graph_writer.write_graph_artifacts(normalized_record, relationship_result)
        write_results.append(write_result)

    graph_nodes = _sorted_nodes(repository)
    graph_relationships = _sorted_relationships(repository)

    return build_graph_workspace_payload_from_snapshot(
        settings=settings,
        saved_raw_records=saved_raw_records,
        graph_snapshot=GraphSnapshot(nodes=graph_nodes, relationships=graph_relationships),
        write_results=write_results,
    )


def build_graph_workspace_payload_from_snapshot(
    *,
    settings: Settings,
    saved_raw_records: list[SavedRawRecord],
    graph_snapshot: GraphSnapshot,
    write_results: list[object] | None = None,
) -> dict[str, Any]:
    """Turn graph repository data into the payload consumed by the React app."""
    graph_nodes = _sort_graph_nodes(graph_snapshot.nodes)
    graph_relationships = _sort_graph_relationships(graph_snapshot.relationships)

    return {
        "title": f"{settings.app_name} Graph Workspace",
        "case": _build_case_payload(
            saved_raw_records=saved_raw_records,
            write_results=list(write_results or []),
            graph_nodes=graph_nodes,
        ),
        "legend": _build_legend(graph_nodes),
        "nodes": _build_frontend_nodes(graph_nodes),
        "edges": _build_frontend_edges(graph_relationships),
        "activity": _build_activity(
            saved_raw_records=saved_raw_records,
            write_results=list(write_results or []),
        ),
    }


def _build_case_payload(
    *,
    saved_raw_records: list[SavedRawRecord],
    write_results: list[object],
    graph_nodes: list[GraphNode],
) -> dict[str, str]:
    """Build the small case summary shown in the left panel."""
    successful_results = [
        result for result in write_results if getattr(result, "status", None) == FetchStatus.SUCCESS
    ]
    status = "ACTIVE" if graph_nodes else "EMPTY"
    if saved_raw_records and not graph_nodes and write_results and not successful_results:
        status = "NO GRAPH DATA"
    case_id = _case_id_for_records(saved_raw_records)

    return {
        "caseId": case_id,
        "scope": f"{len(saved_raw_records)} saved raw records",
        "status": status,
    }


def _build_legend(graph_nodes: list[GraphNode]) -> list[dict[str, str]]:
    """Build a legend from the entity types currently present in the graph."""
    entity_types = sorted({node.entity_type for node in graph_nodes})
    if not entity_types:
        entity_types = ["person", "organization", "domain", "ip", "place"]

    return [
        {
            "label": _title_label(entity_type),
            "description": _legend_description(entity_type),
            "color": _color_for_entity_type(entity_type),
        }
        for entity_type in entity_types
    ]


def _build_frontend_nodes(graph_nodes: list[GraphNode]) -> list[dict[str, Any]]:
    """Convert graph nodes into positioned frontend nodes."""
    positioned_nodes: list[dict[str, Any]] = []
    count = len(graph_nodes)

    for index, graph_node in enumerate(graph_nodes):
        x_position, y_position = _position_for_index(index=index, count=count)
        positioned_nodes.append(
            {
                "id": graph_node.entity_key,
                "label": graph_node.display_value or graph_node.canonical_value,
                "type": graph_node.entity_type,
                "tier": ENTITY_TIERS.get(graph_node.entity_type, "Entity"),
                "status": "Linked",
                "description": _node_description(graph_node),
                "attributes": _node_attributes(graph_node),
                "color": _color_for_entity_type(graph_node.entity_type),
                "x": x_position,
                "y": y_position,
                "radius": _radius_for_entity_type(graph_node.entity_type),
            }
        )

    return positioned_nodes


def _build_frontend_edges(graph_relationships: list[GraphRelationship]) -> list[dict[str, Any]]:
    """Convert graph relationships into frontend edges."""
    return [
        {
            "from": relationship.from_entity_key,
            "to": relationship.to_entity_key,
            "label": _relationship_label(relationship.relationship_type),
            "confidence": relationship.confidence_percent,
        }
        for relationship in graph_relationships
    ]


def _build_activity(
    *,
    saved_raw_records: list[SavedRawRecord],
    write_results: list[object],
) -> list[dict[str, str]]:
    """Build a compact activity feed from saved raw records and write outcomes."""
    if not saved_raw_records:
        return [{"time": "--:--", "text": "No saved raw records are available yet."}]

    activity_items: list[dict[str, str]] = []
    for saved_raw_record, write_result in zip(saved_raw_records[-8:], write_results[-8:], strict=False):
        saved_time = saved_raw_record.saved_at[11:16] if len(saved_raw_record.saved_at) >= 16 else "--:--"
        provider = (
            saved_raw_record.provider.value
            if hasattr(saved_raw_record.provider, "value")
            else str(saved_raw_record.provider)
        )
        status = getattr(
            getattr(write_result, "status", None),
            "value",
            str(getattr(write_result, "status", "")),
        )
        nodes_written = getattr(write_result, "nodes_written", 0)
        relationships_written = getattr(write_result, "relationships_written", 0)
        activity_items.append(
            {
                "time": saved_time,
                "text": (
                    f"{provider} raw record {saved_raw_record.record_id[:8]} processed "
                    f"with graph status {status}; {nodes_written} nodes and {relationships_written} edges."
                ),
            }
        )

    return activity_items


def _sorted_nodes(repository: InMemoryGraphRepository) -> list[GraphNode]:
    """Return graph nodes in a stable frontend order."""
    return [
        repository.nodes_by_key[key]
        for key in sorted(repository.nodes_by_key)
    ]


def _sorted_relationships(repository: InMemoryGraphRepository) -> list[GraphRelationship]:
    """Return graph relationships in a stable frontend order."""
    return [
        repository.relationships_by_key[key]
        for key in sorted(repository.relationships_by_key)
    ]


def _sort_graph_nodes(graph_nodes: list[GraphNode]) -> list[GraphNode]:
    """Return graph nodes in a stable order."""
    return sorted(graph_nodes, key=lambda node: node.entity_key)


def _sort_graph_relationships(graph_relationships: list[GraphRelationship]) -> list[GraphRelationship]:
    """Return graph relationships in a stable order."""
    return sorted(graph_relationships, key=lambda relationship: relationship.relationship_key)


def _case_id_for_records(saved_raw_records: list[SavedRawRecord]) -> str:
    """Return the case id shown in the workspace."""
    case_ids = sorted({record.case_id or "default" for record in saved_raw_records})
    if len(case_ids) == 1:
        return case_ids[0]

    if len(case_ids) > 1:
        return "multiple-cases"

    return "default"


def _position_for_index(*, index: int, count: int) -> tuple[int, int]:
    """Place nodes around a readable ellipse for the SVG graph."""
    if count <= 1:
        return 600, 380

    angle = (2 * math.pi * index) / count
    x_position = 600 + int(math.cos(angle) * 330)
    y_position = 380 + int(math.sin(angle) * 220)
    return x_position, y_position


def _node_description(graph_node: GraphNode) -> str:
    """Build a short node description."""
    return f"{_title_label(graph_node.entity_type)} entity from saved backend evidence."


def _node_attributes(graph_node: GraphNode) -> list[str]:
    """Build compact node attribute chips for the side panel."""
    attributes = [graph_node.entity_type, graph_node.canonical_value]
    for key, value in sorted(graph_node.metadata.items()):
        if value is None or value == "":
            continue

        attributes.append(f"{key}: {value}")
        if len(attributes) >= 4:
            break

    return attributes


def _relationship_label(relationship_type: str) -> str:
    """Turn a machine relationship label into readable UI text."""
    return relationship_type.replace("_", " ")


def _title_label(value: str) -> str:
    """Turn a machine label into a compact title label."""
    return value.replace("_", " ").title()


def _legend_description(entity_type: str) -> str:
    """Return a short legend description for one entity type."""
    if entity_type in {"domain", "ip", "certificate"}:
        return "Infrastructure evidence"

    if entity_type in {"place", "location"}:
        return "Geographic anchor"

    if entity_type in {"email", "phone"}:
        return "Contact identifier"

    return "Investigation entity"


def _color_for_entity_type(entity_type: str) -> str:
    """Return a stable node color."""
    return ENTITY_COLORS.get(entity_type, "#9aa7ad")


def _radius_for_entity_type(entity_type: str) -> int:
    """Return a stable node radius."""
    if entity_type == "person":
        return 18

    if entity_type in {"organization", "domain", "ip", "place", "location"}:
        return 15

    return 13
