"""Schemas for report creation and previews."""

# `Field` gives field descriptions and default values.
from backend.utils.optional_deps import Field
# `BaseModel` gives us plain data containers.
from backend.utils.optional_deps import BaseModel


class ReportCreateRequest(BaseModel):
    """Request body for generating a report."""

    investigation_id: str = Field(default="investigation-demo", description="Investigation to summarize")
    template_name: str = Field(default="basic", description="Report template choice")


class ReportPreview(BaseModel):
    """Lightweight report preview."""

    report_id: str = Field(default="report-demo", description="Report identifier")
    title: str = Field(default="TODO", description="Report title")
    body_preview: str = Field(default="TODO [CORE]: generate a readable summary", description="Short preview text")

