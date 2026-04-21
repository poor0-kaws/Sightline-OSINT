"""Service layer for graph operations."""

# `EntityRecord` is the input shape for graph node writes.
from backend.schemas.entity import EntityRecord
# `GraphEdge` represents a link in the graph.
from backend.schemas.graph import GraphEdge
# `GraphRepository` hides Neo4j-specific details.
from backend.repositories.graph_repository import GraphRepository


# We use a service class so graph workflows can add validation later without changing routes.
class GraphService:
    """Coordinates graph reads and writes."""

    def __init__(self, repository: GraphRepository) -> None:
        self.repository = repository

    def add_entity(self, entity: EntityRecord) -> None:
        """Store one entity node."""
        self.repository.upsert_entity(entity)

    def link_entities(self, edge: GraphEdge) -> None:
        """Store one graph edge."""
        self.repository.create_edge(edge)

    def get_neighbors(self, entity_id: str) -> list[dict]:
        """Return graph neighbors for the investigation canvas."""
        return self.repository.fetch_neighbors(entity_id)

