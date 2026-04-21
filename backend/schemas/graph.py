"""Schemas for graph nodes and edges."""

# `Field` gives simple metadata for each field.
from backend.utils.optional_deps import Field
# `BaseModel` gives structured containers for graph data.
from backend.utils.optional_deps import BaseModel


class GraphNode(BaseModel):
    """Graph node shell."""

    node_id: str = Field(default="node-demo", description="Node identifier")
    label: str = Field(default="TODO", description="Visible node label")


class GraphEdge(BaseModel):
    """Graph edge shell."""

    source_node_id: str = Field(default="node-a", description="Start node id")
    target_node_id: str = Field(default="node-b", description="End node id")
    relationship: str = Field(default="RELATED_TO", description="Edge type")


class GraphLinkRequest(BaseModel):
    """Request body for linking two entities in the graph."""

    left_entity_id: str = Field(default="entity-left", description="First entity to link")
    right_entity_id: str = Field(default="entity-right", description="Second entity to link")
    note: str = Field(default="TODO", description="Why the user thinks these are linked")

