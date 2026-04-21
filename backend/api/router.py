"""Root API router."""

# `APIRouter` groups route modules together.
from backend.utils.optional_deps import APIRouter

# Each route module owns one small slice of the API surface.
from backend.api.routes.entities import router as entities_router
# Each route module owns one small slice of the API surface.
from backend.api.routes.graph import router as graph_router
# Each route module owns one small slice of the API surface.
from backend.api.routes.health import router as health_router
# Each route module owns one small slice of the API surface.
from backend.api.routes.ingest import router as ingest_router
# Each route module owns one small slice of the API surface.
from backend.api.routes.investigations import router as investigations_router
# Each route module owns one small slice of the API surface.
from backend.api.routes.reports import router as reports_router


router = APIRouter(prefix="/api")
router.include_router(health_router)
router.include_router(ingest_router)
router.include_router(entities_router)
router.include_router(graph_router)
router.include_router(investigations_router)
router.include_router(reports_router)

