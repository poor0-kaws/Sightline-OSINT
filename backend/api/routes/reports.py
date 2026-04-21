"""Report route shell."""

# `get_report_service` gives this route access to report generation.
from backend.dependencies import get_report_service
# `ReportCreateRequest` is the request body for creating a report.
from backend.schemas.report import ReportCreateRequest
# `ReportPreview` is the lightweight response model.
from backend.schemas.report import ReportPreview
# `APIRouter` groups related endpoints together.
from backend.utils.optional_deps import APIRouter
# `Depends` wires a route to a service object.
from backend.utils.optional_deps import Depends


router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
def generate_report(
    request: ReportCreateRequest,
    service=Depends(get_report_service),
) -> ReportPreview:
    """Return a placeholder report preview."""
    return service.generate_report(request)

