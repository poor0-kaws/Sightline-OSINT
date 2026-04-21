"""Schemas for investigations and analyst notes."""

# `Field` gives readable defaults and descriptions.
from backend.utils.optional_deps import Field
# `BaseModel` gives structured objects for the API surface.
from backend.utils.optional_deps import BaseModel


class InvestigationRecord(BaseModel):
    """Investigation shell."""

    investigation_id: str = Field(default="investigation-demo", description="Investigation id")
    title: str = Field(default="TODO", description="Investigation title")
    status: str = Field(default="draft", description="Current investigation state")


class AnnotationCreate(BaseModel):
    """Annotation shell added to a link or node."""

    target_id: str = Field(default="entity-demo", description="Node or edge id")
    body: str = Field(default="TODO", description="Analyst note text")

