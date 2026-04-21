"""Service layer for ingestion workflows."""

# `SourceKind` lets us choose the right connector family.
from backend.schemas.ingestion import SourceKind
# `IngestionJobCreate` describes the request to schedule a job.
from backend.schemas.ingestion import IngestionJobCreate
# `IngestionJobStatus` is the response shape for queued jobs.
from backend.schemas.ingestion import IngestionJobStatus


# We use a service class so routes stay thin and the workflow has one home.
class IngestionService:
    """Orchestrates source selection and ingestion job setup."""

    def list_supported_source_types(self) -> list[str]:
        """Return the connector kinds the scaffold knows about."""
        return [kind.value for kind in SourceKind]

    def schedule_ingestion(self, job_request: IngestionJobCreate) -> IngestionJobStatus:
        """Create a placeholder ingestion job."""
        _ = job_request
        # TODO [OPTIONAL]: hand work to Celery once the worker path is real.
        return IngestionJobStatus()

    def preview_payload_shape(self, source_kind: SourceKind) -> dict:
        """Return a tiny preview of what each source type might emit."""
        _ = source_kind
        return {"records": [], "note": "TODO [CORE]: show a realistic normalized preview"}

