"""Entity route shell."""

# `get_resolution_service` gives this route access to entity matching work.
from backend.dependencies import get_resolution_service
# `EntityLinkSuggestion` is the shape of possible entity matches.
from backend.schemas.entity import EntityLinkSuggestion
# `APIRouter` groups related endpoints together.
from backend.utils.optional_deps import APIRouter
# `Depends` wires a route to a service object.
from backend.utils.optional_deps import Depends


router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/suggestions")
def list_entity_suggestions(
    service=Depends(get_resolution_service),
) -> list[EntityLinkSuggestion]:
    """Return placeholder entity match suggestions."""
    _ = service
    # TODO [CORE]: accept filters and return reviewed match candidates.
    return []

