"""Graph route shell."""

# `get_graph_service` gives this route access to graph reads and writes.
from backend.dependencies import get_graph_service
# `GraphEdge` is the shape of a stored relationship.
from backend.schemas.graph import GraphEdge
# `GraphLinkRequest` is the request body for linking entities.
from backend.schemas.graph import GraphLinkRequest
# `MessageResponse` is a small human-readable response body.
from backend.schemas.common import MessageResponse
# `APIRouter` groups related endpoints together.
from backend.utils.optional_deps import APIRouter
# `Depends` wires a route to a service object.
from backend.utils.optional_deps import Depends


router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/links")
def create_graph_link(
    request: GraphLinkRequest,
    service=Depends(get_graph_service),
) -> MessageResponse:
    """Create a placeholder graph link."""
    edge = GraphEdge(
        source_node_id=request.left_entity_id,
        target_node_id=request.right_entity_id,
        relationship="RELATED_TO",
    )
    service.link_entities(edge)
    return MessageResponse(message="graph link stub queued")

