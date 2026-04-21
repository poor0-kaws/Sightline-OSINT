"""Dependency wiring for route handlers."""

# `get_settings` gives us app configuration values.
from backend.config import get_settings
# `GraphRepository` is the graph storage adapter.
from backend.repositories.graph_repository import GraphRepository
# `GraphService` wraps graph repository operations.
from backend.services.graph_service import GraphService
# `IngestionService` handles ingestion job setup.
from backend.services.ingestion_service import IngestionService
# `InvestigationService` handles notes and investigations.
from backend.services.investigation_service import InvestigationService
# `ReportService` handles report generation.
from backend.services.report_service import ReportService
# `ResolutionService` handles entity matching.
from backend.services.resolution_service import ResolutionService
# `StatusService` returns simple demo status values.
from backend.services.status_service import StatusService


def get_ingestion_service() -> IngestionService:
    """Return the ingestion service."""
    return IngestionService()


def get_resolution_service() -> ResolutionService:
    """Return the entity resolution service."""
    return ResolutionService()


def get_graph_service() -> GraphService:
    """Return the graph service."""
    settings = get_settings()
    repository = GraphRepository(
        neo4j_url=settings.neo4j_url,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
    )
    return GraphService(repository=repository)


def get_investigation_service() -> InvestigationService:
    """Return the investigation service."""
    return InvestigationService()


def get_report_service() -> ReportService:
    """Return the report service."""
    return ReportService()


def get_status_service() -> StatusService:
    """Return the status service."""
    return StatusService()

