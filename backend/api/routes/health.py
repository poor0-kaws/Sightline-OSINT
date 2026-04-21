"""Health route shell."""

# `StatusResponse` is the response model for health checks.
from backend.schemas.common import StatusResponse
# `APIRouter` groups related endpoints together.
from backend.utils.optional_deps import APIRouter


router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
def health_check() -> StatusResponse:
    """Return a tiny health response."""
    return StatusResponse()

