"""Service layer for report generation."""

# `ReportCreateRequest` describes the report request coming from the API.
from backend.schemas.report import ReportCreateRequest
# `ReportPreview` is the lightweight response shape.
from backend.schemas.report import ReportPreview


# We use a service class because report generation will likely grow prompts, templates, and export paths.
class ReportService:
    """Shell for report generation."""

    def generate_report(self, request: ReportCreateRequest) -> ReportPreview:
        """Generate a report preview."""
        _ = request
        # TODO [CORE]: choose report sections, narrative style, evidence ordering, and export format.
        return ReportPreview()

