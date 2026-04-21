"""Investigation route shell."""

# `get_investigation_service` gives this route access to investigation workflows.
from backend.dependencies import get_investigation_service
# `AnnotationCreate` is the request body for adding a note.
from backend.schemas.investigation import AnnotationCreate
# `InvestigationRecord` is the investigation response model.
from backend.schemas.investigation import InvestigationRecord
# `MessageResponse` is a tiny response model.
from backend.schemas.common import MessageResponse
# `APIRouter` groups related endpoints together.
from backend.utils.optional_deps import APIRouter
# `Depends` wires a route to a service object.
from backend.utils.optional_deps import Depends


router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("")
def create_investigation(
    title: str = "Untitled Investigation",
    service=Depends(get_investigation_service),
) -> InvestigationRecord:
    """Create a placeholder investigation."""
    return service.create_investigation(title)


@router.post("/annotations")
def add_annotation(
    annotation: AnnotationCreate,
    service=Depends(get_investigation_service),
) -> MessageResponse:
    """Attach a placeholder annotation."""
    _ = service.add_annotation(annotation)
    return MessageResponse(message="annotation stub queued")

