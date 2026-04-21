"""Service layer for investigations and annotations."""

# `AnnotationCreate` is the request body for adding a note.
from backend.schemas.investigation import AnnotationCreate
# `InvestigationRecord` is the investigation model.
from backend.schemas.investigation import InvestigationRecord


# We use a service class so future collaboration logic has a clear home.
class InvestigationService:
    """Shell for investigation workflows."""

    def create_investigation(self, title: str) -> InvestigationRecord:
        """Create a new investigation shell."""
        _ = title
        # TODO [OPTIONAL]: persist investigations once you choose the storage shape.
        return InvestigationRecord()

    def add_annotation(self, annotation: AnnotationCreate) -> dict:
        """Attach an annotation to a node or edge."""
        _ = annotation
        # TODO [OPTIONAL]: decide where annotations live and how version history works.
        return {"status": "queued", "note": "annotation stub only"}

