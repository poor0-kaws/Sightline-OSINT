"""Repositories for writing graph nodes and edges."""

from __future__ import annotations

from typing import Any
from typing import Protocol

from backend.graph.schemas import GraphNode
from backend.graph.schemas import GraphRelationship
from backend.graph.schemas import GraphSnapshot


class GraphRepositoryProtocol(Protocol):
    """Small contract that any graph repository must follow."""

    def write_graph_batch(
        self,
        *,
        nodes: list[GraphNode],
        relationships: list[GraphRelationship],
    ) -> None:
        """Write one fully validated graph batch."""

    def read_graph(self, case_id: str = "") -> GraphSnapshot:
        """Read graph nodes and relationships."""


class InMemoryGraphRepository:
    """Tiny in-memory graph repository used by tests."""

    def __init__(self) -> None:
        self.nodes_by_key: dict[str, GraphNode] = {}
        self.relationships_by_key: dict[str, GraphRelationship] = {}

    def write_graph_batch(
        self,
        *,
        nodes: list[GraphNode],
        relationships: list[GraphRelationship],
    ) -> None:
        """Store graph writes in memory."""
        updated_nodes = dict(self.nodes_by_key)
        updated_relationships = dict(self.relationships_by_key)

        for node in nodes:
            updated_nodes[node.entity_key] = node

        for relationship in relationships:
            updated_relationships[relationship.relationship_key] = relationship

        self.nodes_by_key = updated_nodes
        self.relationships_by_key = updated_relationships

    def read_graph(self, case_id: str = "") -> GraphSnapshot:
        """Return the current in-memory graph."""
        filtered_nodes = {
            key: node
            for key, node in self.nodes_by_key.items()
            if self._matches_case_id(node.metadata, case_id)
        }
        filtered_relationships = {
            key: relationship
            for key, relationship in self.relationships_by_key.items()
            if self._matches_case_id(relationship.metadata, case_id)
        }
        return GraphSnapshot(
            nodes=[filtered_nodes[key] for key in sorted(filtered_nodes)],
            relationships=[
                filtered_relationships[key]
                for key in sorted(filtered_relationships)
            ],
        )

    def _matches_case_id(self, metadata: dict[str, Any], case_id: str) -> bool:
        """Return true when a graph object belongs in the requested case."""
        cleaned_case_id = case_id.strip() if isinstance(case_id, str) else ""
        if not cleaned_case_id:
            return True

        return metadata.get("case_id") == cleaned_case_id


class Neo4jGraphRepository:
    """Batch graph writer that speaks simple Cypher to a Neo4j-like driver."""

    NODE_BATCH_QUERY = """
    UNWIND $nodes AS node
    MERGE (n:Entity {entity_key: node.entity_key})
    SET
      n.entity_type = node.entity_type,
      n.canonical_value = node.canonical_value,
      n.display_value = node.display_value,
      n.metadata = node.metadata
    """

    RELATIONSHIP_BATCH_QUERY = """
    UNWIND $relationships AS relationship
    MATCH (from_node:Entity {entity_key: relationship.from_entity_key})
    MATCH (to_node:Entity {entity_key: relationship.to_entity_key})
    MERGE (from_node)-[r:RELATED_TO {relationship_key: relationship.relationship_key}]->(to_node)
    SET
      r.relationship_type = relationship.relationship_type,
      r.confidence_percent = relationship.confidence_percent,
      r.evidence_record_id = relationship.evidence_record_id,
      r.metadata = relationship.metadata
    """

    GRAPH_READ_QUERY = """
    MATCH (n:Entity)
    WHERE $case_id = '' OR n.metadata.case_id = $case_id
    WITH collect(n) AS nodes
    OPTIONAL MATCH (from_node:Entity)-[r:RELATED_TO]->(to_node:Entity)
    WHERE $case_id = '' OR r.metadata.case_id = $case_id
    RETURN nodes, collect({
      relationship_key: r.relationship_key,
      relationship_type: r.relationship_type,
      from_entity_key: from_node.entity_key,
      to_entity_key: to_node.entity_key,
      confidence_percent: r.confidence_percent,
      evidence_record_id: r.evidence_record_id,
      metadata: r.metadata
    }) AS relationships
    """

    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def write_graph_batch(
        self,
        *,
        nodes: list[GraphNode],
        relationships: list[GraphRelationship],
    ) -> None:
        """Write all nodes first, then all relationships, in one session."""
        with self.driver.session() as session:
            if nodes:
                session.run(
                    self.NODE_BATCH_QUERY,
                    parameters={"nodes": [self._node_to_dict(node) for node in nodes]},
                )

            if relationships:
                session.run(
                    self.RELATIONSHIP_BATCH_QUERY,
                    parameters={
                        "relationships": [
                            self._relationship_to_dict(relationship)
                            for relationship in relationships
                        ]
                    },
                )

    def read_graph(self, case_id: str = "") -> GraphSnapshot:
        """Read all graph nodes and relationships from Neo4j."""
        with self.driver.session() as session:
            result = session.run(self.GRAPH_READ_QUERY, parameters={"case_id": self._clean_case_id(case_id)})
            row = result.single()

        if row is None:
            return GraphSnapshot()

        return GraphSnapshot(
            nodes=[
                self._node_from_neo4j(node)
                for node in row.get("nodes", [])
                if node is not None
            ],
            relationships=[
                self._relationship_from_neo4j(relationship)
                for relationship in row.get("relationships", [])
                if self._has_relationship_payload(relationship)
            ],
        )

    def _node_to_dict(self, node: GraphNode) -> dict[str, Any]:
        """Turn one graph node into a Cypher-friendly dictionary."""
        return {
            "entity_key": node.entity_key,
            "entity_type": node.entity_type,
            "canonical_value": node.canonical_value,
            "display_value": node.display_value,
            "metadata": dict(node.metadata),
        }

    def _relationship_to_dict(self, relationship: GraphRelationship) -> dict[str, Any]:
        """Turn one graph edge into a Cypher-friendly dictionary."""
        return {
            "relationship_key": relationship.relationship_key,
            "relationship_type": relationship.relationship_type,
            "from_entity_key": relationship.from_entity_key,
            "to_entity_key": relationship.to_entity_key,
            "confidence_percent": relationship.confidence_percent,
            "evidence_record_id": relationship.evidence_record_id,
            "metadata": dict(relationship.metadata),
        }

    def _node_from_neo4j(self, node: Any) -> GraphNode:
        """Turn one Neo4j node-like object into a graph node."""
        return GraphNode(
            entity_key=str(node.get("entity_key", "")),
            entity_type=str(node.get("entity_type", "")),
            canonical_value=str(node.get("canonical_value", "")),
            display_value=str(node.get("display_value", "")),
            metadata=self._safe_metadata(node.get("metadata")),
        )

    def _relationship_from_neo4j(self, relationship: dict[str, Any]) -> GraphRelationship:
        """Turn one Neo4j relationship-like dict into a graph relationship."""
        return GraphRelationship(
            relationship_key=str(relationship.get("relationship_key", "")),
            relationship_type=str(relationship.get("relationship_type", "")),
            from_entity_key=str(relationship.get("from_entity_key", "")),
            to_entity_key=str(relationship.get("to_entity_key", "")),
            confidence_percent=int(relationship.get("confidence_percent") or 0),
            evidence_record_id=str(relationship.get("evidence_record_id", "")),
            metadata=self._safe_metadata(relationship.get("metadata")),
        )

    def _has_relationship_payload(self, value: object) -> bool:
        """Return true when an optional Neo4j relationship row has real data."""
        if not isinstance(value, dict):
            return False

        return bool(value.get("relationship_key"))

    def _safe_metadata(self, value: object) -> dict[str, Any]:
        """Return metadata as a plain dictionary."""
        if isinstance(value, dict):
            return dict(value)

        return {}

    def _clean_case_id(self, value: object) -> str:
        """Return a safe case id filter."""
        if not isinstance(value, str):
            return ""

        return value.strip()
