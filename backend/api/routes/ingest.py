"""Ingestion route shell."""

# `get_ingestion_service` gives this route access to the ingestion workflow shell.
from backend.dependencies import get_ingestion_service
# `IngestionJobCreate` is the request body for queuing work.
from backend.schemas.ingestion import IngestionJobCreate
# `IngestionJobStatus` is the response body for queued work.
from backend.schemas.ingestion import IngestionJobStatus
# `APIRouter` groups related endpoints together.
from backend.utils.optional_deps import APIRouter
# `Depends` wires a route to a service object.
from backend.utils.optional_deps import Depends


router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/jobs")
def create_ingestion_job(
    job_request: IngestionJobCreate,
    service=Depends(get_ingestion_service),
) -> IngestionJobStatus:
    """Create a placeholder ingestion job."""
    return service.schedule_ingestion(job_request)

