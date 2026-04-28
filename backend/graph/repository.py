"""Repositories for writing graph nodes and edges."""

from __future__ import annotations

from typing import Any
from typing import Protocol

from backend.graph.schemas import GraphNode
from backend.graph.schemas import GraphRelationship


class GraphRepositoryProtocol(Protocol):
    """Small contract that any graph repository must follow."""

    def write_graph_batch(
        self,
        *,
        nodes: list[GraphNode],
        relationships: list[GraphRelationship],
    ) -> None:
        """Write one fully validated graph batch."""


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
                    parameters={"relationships": [self._relationship_to_dict(relationship) for relationship in relationships]},
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
