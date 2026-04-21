"""Service layer for ingestion workflows."""

# `build_source_preview` returns an example raw payload for a source kind.
from backend.connectors import build_source_preview
# `list_source_definitions` returns human-friendly source metadata.
from backend.connectors import list_source_definitions
# `SourceKind` lets us choose the right connector family.
from backend.schemas.ingestion import SourceKind
# `IngestionJobCreate` describes the request to schedule a job.
from backend.schemas.ingestion import IngestionJobCreate
# `IngestionJobStatus` is the response shape for queued jobs.
from backend.schemas.ingestion import IngestionJobStatus
from backend.schemas.ingestion import SourceDefinition
from backend.schemas.ingestion import SourcePreview


# We use a service class so routes stay thin and the workflow has one home.
class IngestionService:
    """Orchestrates source selection and ingestion job setup."""

    def list_supported_source_types(self) -> list[str]:
        """Return the connector kinds the scaffold knows about."""
        return [kind.value for kind in SourceKind]

    def list_supported_sources(self) -> list[SourceDefinition]:
        """Return plain-English descriptions of the supported sources."""
        return list_source_definitions()

    def schedule_ingestion(self, job_request: IngestionJobCreate) -> IngestionJobStatus:
        """Create a placeholder ingestion job."""
        _ = job_request
        # TODO [OPTIONAL]: hand work to Celery once the worker path is real.
        return IngestionJobStatus()

    def preview_payload_shape(self, source_kind: SourceKind) -> SourcePreview:
        """Return a tiny preview of the raw records one source type can emit."""
        return build_source_preview(source_kind)
