"""End-to-end pipeline that writes graph data from one source request."""

from __future__ import annotations

from backend.graph.repository import GraphRepositoryProtocol
from backend.graph.schemas import GraphWriteResult
from backend.graph.service import GraphWriteService
from backend.relationships import extract_relationships_from_normalized_record
from backend.services.provider_processing_pipeline import ProviderProcessingPipeline


class GraphProcessingPipeline:
    """Run the current full ingest-to-graph-write pipeline."""

    def __init__(
        self,
        *,
        repository: GraphRepositoryProtocol,
        provider_processing_pipeline: ProviderProcessingPipeline | None = None,
        graph_write_service: GraphWriteService | None = None,
    ) -> None:
        self.provider_processing_pipeline = provider_processing_pipeline or ProviderProcessingPipeline()
        self.graph_write_service = graph_write_service or GraphWriteService(repository)

    def run(self, source_request: object) -> GraphWriteResult:
        """Fetch, save, normalize, extract relationships, and write the graph batch."""
        normalized_record = self.provider_processing_pipeline.run(source_request)
        relationship_result = extract_relationships_from_normalized_record(normalized_record)
        return self.graph_write_service.write_graph_artifacts(normalized_record, relationship_result)
