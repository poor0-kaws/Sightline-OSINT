"""Schemas for normalized entities."""

# `Field` gives default values and descriptions.
from backend.utils.optional_deps import Field
# `BaseModel` gives us simple structured objects.
from backend.utils.optional_deps import BaseModel


class EntityRecord(BaseModel):
    """Normalized entity shell."""

    entity_id: str = Field(default="entity-demo", description="Stable entity identifier")
    entity_type: str = Field(default="unknown", description="Type like person or domain")
    display_name: str = Field(default="TODO", description="Human-readable label")


class EntityLinkSuggestion(BaseModel):
    """Potential link between two entities."""

    left_entity_id: str = Field(default="entity-left", description="First entity id")
    right_entity_id: str = Field(default="entity-right", description="Second entity id")
    confidence: float = Field(default=0.0, description="Placeholder score")
    reason: str = Field(default="TODO [CORE]: explain matching evidence", description="Why the match might be real")

