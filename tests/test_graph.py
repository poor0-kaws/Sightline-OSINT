"""Tests for graph database writes and graph write orchestration."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from backend.normalization import NormalizedEntity
from backend.normalization import NormalizedRecord
from backend.relationships import EntityReference
from backend.relationships import ExtractedRelationship
from backend.relationships import RelationshipExtractionResult
from backend.relationships import RelationshipType
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind
from backend.schemas.ingestion import SourceConfig
from backend.schemas.ingestion import SourceRequest
from backend.schemas.ingestion import SourceKind
from backend.settings import Settings


def test_graph_repository_factory_builds_memory_repository() -> None:
    """Memory mode should create the local repository used by tests and development."""
    from backend.graph import InMemoryGraphRepository
    from backend.graph import build_graph_repository

    repository = build_graph_repository(Settings(graph_repository_kind="memory"))

    assert isinstance(repository, InMemoryGraphRepository)


def test_graph_repository_factory_builds_neo4j_repository_with_optional_driver(monkeypatch) -> None:
    """Neo4j mode should pass settings into the optional Neo4j driver."""
    from backend.graph import Neo4jGraphRepository
    from backend.graph import build_graph_repository

    class FakeGraphDatabase:
        @staticmethod
        def driver(url: str, auth: tuple[str, str] | None = None) -> dict[str, object]:
            return {"url": url, "auth": auth}

    monkeypatch.setitem(sys.modules, "neo4j", SimpleNamespace(GraphDatabase=FakeGraphDatabase))

    repository = build_graph_repository(
        Settings(
            graph_repository_kind="neo4j",
            neo4j_url="bolt://graph.example:7687",
            neo4j_username="neo4j",
            neo4j_password="password",
        )
    )

    assert isinstance(repository, Neo4jGraphRepository)
    assert repository.driver == {
        "url": "bolt://graph.example:7687",
        "auth": ("neo4j", "password"),
    }


def test_in_memory_graph_repository_reads_graph_with_case_filter() -> None:
    """Graph reads should respect case ids stored in metadata."""
    from backend.graph import GraphNode
    from backend.graph import InMemoryGraphRepository

    repository = InMemoryGraphRepository()
    repository.write_graph_batch(
        nodes=[
            GraphNode(
                entity_key="case-alpha:person:alice",
                entity_type="person",
                canonical_value="alice",
                display_value="Alice",
                metadata={"case_id": "case-alpha"},
            ),
            GraphNode(
                entity_key="case-beta:person:bob",
                entity_type="person",
                canonical_value="bob",
                display_value="Bob",
                metadata={"case_id": "case-beta"},
            ),
        ],
        relationships=[],
    )

    graph_snapshot = repository.read_graph(case_id="case-alpha")

    assert len(graph_snapshot.nodes) == 1
    assert graph_snapshot.nodes[0].display_value == "Alice"


def test_graph_write_service_dedupes_nodes_and_relationships_before_writing() -> None:
    """Duplicate nodes and edges should only be written once."""
    from backend.graph import GraphWriteService
    from backend.graph import InMemoryGraphRepository

    normalized_record = NormalizedRecord(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="graph-raw-1",
        query={"case_id": "case-1"},
        status=FetchStatus.SUCCESS,
        normalized_data={"fields": {}},
        entities=[
            NormalizedEntity(entity_type="person", canonical_value="alice ng", display_value="Alice Ng"),
            NormalizedEntity(entity_type="person", canonical_value="alice ng", display_value="Alice Ng"),
            NormalizedEntity(entity_type="email", canonical_value="alice@personalmail.org", display_value="alice@personalmail.org"),
        ],
        metadata={},
    )
    relationship_result = RelationshipExtractionResult(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="graph-raw-1",
        query={"case_id": "case-1"},
        status=FetchStatus.SUCCESS,
        relationships=[
            ExtractedRelationship(
                relationship_id="rel-1",
                relationship_type=RelationshipType.PERSON_USES_EMAIL,
                from_entity=EntityReference(
                    entity_id="person-1",
                    entity_type="person",
                    canonical_value="alice ng",
                    display_value="Alice Ng",
                ),
                to_entity=EntityReference(
                    entity_id="email-1",
                    entity_type="email",
                    canonical_value="alice@personalmail.org",
                    display_value="alice@personalmail.org",
                ),
                confidence_percent=95,
                evidence_record_id="graph-raw-1",
            ),
            ExtractedRelationship(
                relationship_id="rel-2",
                relationship_type=RelationshipType.PERSON_USES_EMAIL,
                from_entity=EntityReference(
                    entity_id="person-2",
                    entity_type="person",
                    canonical_value="alice ng",
                    display_value="Alice Ng",
                ),
                to_entity=EntityReference(
                    entity_id="email-2",
                    entity_type="email",
                    canonical_value="alice@personalmail.org",
                    display_value="alice@personalmail.org",
                ),
                confidence_percent=95,
                evidence_record_id="graph-raw-1",
            ),
            ExtractedRelationship(
                relationship_id="rel-3",
                relationship_type=RelationshipType.PERSON_ASSOCIATED_WITH_COMPANY,
                from_entity=EntityReference(
                    entity_id="person-3",
                    entity_type="person",
                    canonical_value="alice ng",
                    display_value="Alice Ng",
                ),
                to_entity=EntityReference(
                    entity_id="company-1",
                    entity_type="company",
                    canonical_value="openai",
                    display_value="OpenAI LLC",
                ),
                confidence_percent=80,
                evidence_record_id="graph-raw-1",
            ),
        ],
        metadata={},
    )

    repository = InMemoryGraphRepository()
    service = GraphWriteService(repository)

    result = service.write_graph_artifacts(normalized_record, relationship_result)

    assert result.status == FetchStatus.SUCCESS
    assert result.nodes_written == 3
    assert result.relationships_written == 2
    assert len(repository.nodes_by_key) == 3
    assert len(repository.relationships_by_key) == 2


def test_graph_write_service_writes_standalone_entities_when_relationships_have_no_results() -> None:
    """Clean entities should still become graph nodes even without edges."""
    from backend.graph import GraphWriteService
    from backend.graph import InMemoryGraphRepository

    normalized_record = NormalizedRecord(
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        raw_record_id="graph-raw-2",
        query={"lat": 39.7684, "lon": -86.1581},
        status=FetchStatus.SUCCESS,
        normalized_data={"place": {}},
        entities=[
            NormalizedEntity(
                entity_type="place",
                canonical_value="indianapolis|indiana|us",
                display_value="Indianapolis, Indiana, US",
            )
        ],
        metadata={},
    )
    relationship_result = RelationshipExtractionResult(
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        raw_record_id="graph-raw-2",
        query={"lat": 39.7684, "lon": -86.1581},
        status=FetchStatus.NO_RESULTS,
        relationships=[],
        metadata={},
    )

    repository = InMemoryGraphRepository()
    service = GraphWriteService(repository)

    result = service.write_graph_artifacts(normalized_record, relationship_result)

    assert result.status == FetchStatus.SUCCESS
    assert result.nodes_written == 1
    assert result.relationships_written == 0
    assert len(repository.nodes_by_key) == 1


def test_graph_write_service_rejects_mismatched_record_ids_before_any_write() -> None:
    """Normalized and relationship artifacts must belong to the same record."""
    from backend.graph import GraphWriteService
    from backend.graph import InMemoryGraphRepository

    normalized_record = NormalizedRecord(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="graph-raw-3",
        query="8.8.8.8",
        status=FetchStatus.SUCCESS,
        normalized_data={},
        entities=[NormalizedEntity(entity_type="ip", canonical_value="8.8.8.8", display_value="8.8.8.8")],
        metadata={},
    )
    relationship_result = RelationshipExtractionResult(
        provider=ProviderKind.IPINFO,
        source_type=SourceKind.API,
        raw_record_id="graph-raw-other",
        query="8.8.8.8",
        status=FetchStatus.NO_RESULTS,
        relationships=[],
        metadata={},
    )

    repository = InMemoryGraphRepository()
    service = GraphWriteService(repository)

    result = service.write_graph_artifacts(normalized_record, relationship_result)

    assert result.status == FetchStatus.ERROR
    assert result.error is not None
    assert result.error.code == "graph_record_mismatch"
    assert len(repository.nodes_by_key) == 0
    assert len(repository.relationships_by_key) == 0


def test_graph_write_service_rejects_broken_relationship_endpoints_before_writing() -> None:
    """A relationship with a blank endpoint key should fail the whole batch."""
    from backend.graph import GraphWriteService
    from backend.graph import InMemoryGraphRepository

    normalized_record = NormalizedRecord(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        case_id="case-graph-error",
        raw_record_id="graph-raw-4",
        query={},
        status=FetchStatus.SUCCESS,
        normalized_data={},
        entities=[],
        metadata={},
    )
    relationship_result = RelationshipExtractionResult(
        provider=ProviderKind.MANUAL_INPUT,
        source_type=SourceKind.MANUAL,
        raw_record_id="graph-raw-4",
        query={},
        status=FetchStatus.SUCCESS,
        relationships=[
            ExtractedRelationship(
                relationship_id="rel-bad",
                relationship_type=RelationshipType.PERSON_USES_EMAIL,
                from_entity=EntityReference(
                    entity_id="person-1",
                    entity_type="person",
                    canonical_value="alice ng",
                    display_value="Alice Ng",
                ),
                to_entity=EntityReference(
                    entity_id="email-bad",
                    entity_type="email",
                    canonical_value="",
                    display_value="alice@personalmail.org",
                ),
                confidence_percent=95,
                evidence_record_id="graph-raw-4",
            )
        ],
        metadata={},
    )

    repository = InMemoryGraphRepository()
    service = GraphWriteService(repository)

    result = service.write_graph_artifacts(normalized_record, relationship_result)

    assert result.status == FetchStatus.ERROR
    assert result.error is not None
    assert result.error.code == "graph_bad_relationship"
    assert result.provider == ProviderKind.MANUAL_INPUT
    assert result.raw_record_id == "graph-raw-4"
    assert len(repository.nodes_by_key) == 0
    assert len(repository.relationships_by_key) == 0


def test_graph_write_service_passes_through_upstream_relationship_error_without_writing() -> None:
    """If relationship extraction failed, graph writes should not start."""
    from backend.graph import GraphWriteService
    from backend.graph import InMemoryGraphRepository

    normalized_record = NormalizedRecord(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        raw_record_id="graph-raw-5",
        query="example.com",
        status=FetchStatus.SUCCESS,
        normalized_data={},
        entities=[],
        metadata={},
    )
    relationship_result = RelationshipExtractionResult(
        provider=ProviderKind.CRT_SH,
        source_type=SourceKind.SCRAPER,
        raw_record_id="graph-raw-5",
        query="example.com",
        status=FetchStatus.ERROR,
        error=ProviderError(code="relationship_bad_normalized_data", message="Broken certificate data."),
        relationships=[],
        metadata={},
    )

    repository = InMemoryGraphRepository()
    service = GraphWriteService(repository)

    result = service.write_graph_artifacts(normalized_record, relationship_result)

    assert result.status == FetchStatus.ERROR
    assert result.error is not None
    assert result.error.code == "relationship_bad_normalized_data"
    assert len(repository.nodes_by_key) == 0
    assert len(repository.relationships_by_key) == 0


def test_graph_write_service_returns_clean_error_when_repository_write_fails() -> None:
    """Repository failures should become graph-layer errors."""
    from backend.graph import GraphWriteService
    from backend.graph import InMemoryGraphRepository

    class FailingRepository(InMemoryGraphRepository):
        def write_graph_batch(self, *, nodes, relationships) -> None:  # type: ignore[override]
            raise RuntimeError("graph database unavailable")

    normalized_record = NormalizedRecord(
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        raw_record_id="graph-raw-6",
        query={},
        status=FetchStatus.SUCCESS,
        normalized_data={},
        entities=[NormalizedEntity(entity_type="place", canonical_value="x|y|z", display_value="X, Y, Z")],
        metadata={},
    )
    relationship_result = RelationshipExtractionResult(
        provider=ProviderKind.NOMINATIM,
        source_type=SourceKind.API,
        raw_record_id="graph-raw-6",
        query={},
        status=FetchStatus.NO_RESULTS,
        relationships=[],
        metadata={},
    )

    service = GraphWriteService(FailingRepository())

    result = service.write_graph_artifacts(normalized_record, relationship_result)

    assert result.status == FetchStatus.ERROR
    assert result.error is not None
    assert result.error.code == "graph_write_failed"


def test_neo4j_graph_repository_runs_batch_merge_queries() -> None:
    """The Neo4j repository should translate nodes and edges into merge queries."""
    from backend.graph import GraphNode
    from backend.graph import GraphRelationship
    from backend.graph import Neo4jGraphRepository

    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        def run(self, query: str, parameters: dict[str, object]) -> None:
            self.calls.append((query, parameters))

        def __enter__(self) -> "FakeSession":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    class FakeDriver:
        def __init__(self) -> None:
            self.session_instance = FakeSession()

        def session(self) -> FakeSession:
            return self.session_instance

    driver = FakeDriver()
    repository = Neo4jGraphRepository(driver)

    repository.write_graph_batch(
        nodes=[
            GraphNode(
                entity_key="person:alice-ng",
                entity_type="person",
                canonical_value="alice ng",
                display_value="Alice Ng",
                metadata={"source": "manual"},
            )
        ],
        relationships=[
            GraphRelationship(
                relationship_key="person_uses_email|person:alice-ng|email:alice",
                relationship_type="person_uses_email",
                from_entity_key="person:alice-ng",
                to_entity_key="email:alice",
                confidence_percent=95,
                evidence_record_id="graph-raw-7",
                metadata={"source": "manual"},
            )
        ],
    )

    calls = driver.session_instance.calls

    assert len(calls) == 2
    assert "UNWIND $nodes AS node" in calls[0][0]
    assert calls[0][1]["nodes"][0]["entity_key"] == "person:alice-ng"
    assert "UNWIND $relationships AS relationship" in calls[1][0]
    assert calls[1][1]["relationships"][0]["relationship_key"] == "person_uses_email|person:alice-ng|email:alice"


def test_graph_processing_pipeline_runs_end_to_end_and_writes_into_repository(
    tmp_path: object,
    monkeypatch,
) -> None:
    """The graph pipeline should go from source request all the way to graph nodes and edges."""
    from backend.graph import InMemoryGraphRepository
    from backend.services.graph_processing_pipeline import GraphProcessingPipeline

    monkeypatch.setenv("RAW_STORAGE_PATH", str(tmp_path))

    repository = InMemoryGraphRepository()
    pipeline = GraphProcessingPipeline(repository=repository)

    result = pipeline.run(
        SourceRequest(
            source=SourceConfig(
                source_id="graph-source-1",
                provider=ProviderKind.MANUAL_INPUT,
                source_kind=SourceKind.MANUAL,
            ),
            query={
                "note": "Potential link for Alice Ng",
                "full_name": "Alice Ng",
                "email": "alice@personalmail.org",
                "phone": "+1 (317) 555-0101",
                "company_name": "OpenAI LLC",
            },
        )
    )

    assert result.status == FetchStatus.SUCCESS
    assert result.nodes_written == 4
    assert result.relationships_written == 3
    assert len(repository.nodes_by_key) == 4
    assert len(repository.relationships_by_key) == 3
