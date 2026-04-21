"""Graph storage shell."""

# `GraphDatabase` creates Neo4j drivers when the real dependency exists.
from backend.utils.optional_deps import GraphDatabase
# `NEO4J_AVAILABLE` tells you if the real Neo4j driver is installed.
from backend.utils.optional_deps import NEO4J_AVAILABLE

# `EntityRecord` is the normalized node input shape.
from backend.schemas.entity import EntityRecord
# `GraphEdge` describes graph links.
from backend.schemas.graph import GraphEdge


# We use a repository class so database details stay in one place.
class GraphRepository:
    """Storage adapter shell for Neo4j."""

    def __init__(self, neo4j_url: str, neo4j_user: str, neo4j_password: str) -> None:
        self.neo4j_url = neo4j_url
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None

    def connect(self) -> None:
        """Create a Neo4j driver when dependencies are installed."""
        if not NEO4J_AVAILABLE:
            return

        # TODO [OPTIONAL]: add connection health checks and retry rules.
        self.driver = GraphDatabase.driver(
            self.neo4j_url,
            auth=(self.neo4j_user, self.neo4j_password),
        )

    def upsert_entity(self, entity: EntityRecord) -> None:
        """Store or update one entity node."""
        _ = entity
        # TODO [CORE]: define node labels, merge keys, and property mapping rules.
        return None

    def create_edge(self, edge: GraphEdge) -> None:
        """Store a link between two nodes."""
        _ = edge
        # TODO [CORE]: define edge types, merge rules, and evidence attachment.
        return None

    def fetch_neighbors(self, entity_id: str) -> list[dict]:
        """Return nearby nodes for a given entity."""
        _ = entity_id
        # TODO [CORE]: decide what neighborhood query the investigation canvas needs.
        return []

