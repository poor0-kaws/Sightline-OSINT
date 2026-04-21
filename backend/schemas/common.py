"""Common schema objects reused across routes."""

# `Field` lets us attach simple descriptions to schema fields.
from backend.utils.optional_deps import Field
# `BaseModel` gives us readable request and response containers.
from backend.utils.optional_deps import BaseModel


class MessageResponse(BaseModel):
    """Simple message payload for basic endpoints."""

    message: str = Field(default="stub response", description="Human-readable message")


class StatusResponse(BaseModel):
    """Small health payload for status endpoints."""

    status: str = Field(default="ok", description="Short system status")
    detail: str = Field(default="skeleton only", description="Extra context for humans")

