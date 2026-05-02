"""Service layer for validating and writing graph artifacts."""

from __future__ import annotations

from typing import Any

from backend.graph.repository import GraphRepositoryProtocol
from backend.graph.schemas import GraphNode
from backend.graph.schemas import GraphRelationship
from backend.graph.schemas import GraphWriteResult
from backend.normalization.schemas import NormalizedEntity
from backend.normalization.schemas import NormalizedRecord
from backend.relationships.common import normalize_company_canonical
from backend.relationships.schemas import EntityReference
from backend.relationships.schemas import ExtractedRelationship
from backend.relationships.schemas import RelationshipExtractionResult
from backend.schemas.error_codes import ErrorCode
from backend.schemas.ingestion import FetchStatus
from backend.schemas.ingestion import ProviderError
from backend.schemas.ingestion import ProviderKind


class GraphWriteService:
    """Validate graph artifacts and hand them to a repository in one batch."""

    def __init__(self, repository: GraphRepositoryProtocol) -> None:
        self.repository = repository

    def write_graph_artifacts(
        self,
        normalized_record: NormalizedRecord,
        relationship_result: RelationshipExtractionResult,
    ) -> GraphWriteResult:
        """Write one record's graph-ready nodes and edges."""
        if normalized_record.status != FetchStatus.SUCCESS:
            return self._build_passthrough_result(normalized_record)

        if normalized_record.raw_record_id != relationship_result.raw_record_id:
            return self._build_error_result(
                normalized_record,
                code=ErrorCode.GRAPH_RECORD_MISMATCH,
                message="Normalized data and relationship data must come from the same raw record.",
            )

        if relationship_result.status == FetchStatus.ERROR:
            return GraphWriteResult(
                provider=self._safe_provider(normalized_record.provider),
                source_type=normalized_record.source_type,
                raw_record_id=normalized_record.raw_record_id,
                query=normalized_record.query,
                status=FetchStatus.ERROR,
                error=relationship_result.error,
                nodes_written=0,
                relationships_written=0,
                metadata=dict(normalized_record.metadata),
            )

        graph_nodes = self._collect_graph_nodes(normalized_record, relationship_result)
        if isinstance(graph_nodes, GraphWriteResult):
            return graph_nodes

        graph_relationships = self._collect_graph_relationships(
            relationship_result,
            case_id=normalized_record.case_id,
        )
        if isinstance(graph_relationships, GraphWriteResult):
            return graph_relationships

        if not graph_nodes and not graph_relationships:
            return GraphWriteResult(
                provider=self._safe_provider(normalized_record.provider),
                source_type=normalized_record.source_type,
                raw_record_id=normalized_record.raw_record_id,
                query=normalized_record.query,
                status=FetchStatus.NO_RESULTS,
                error=None,
                nodes_written=0,
                relationships_written=0,
                metadata=dict(normalized_record.metadata),
            )

        try:
            self.repository.write_graph_batch(nodes=graph_nodes, relationships=graph_relationships)
        except Exception as exc:
            return self._build_error_result(
                normalized_record,
                code=ErrorCode.GRAPH_WRITE_FAILED,
                message=f"Graph write failed: {exc}",
            )

        metadata = dict(normalized_record.metadata)
        metadata["nodes_written"] = len(graph_nodes)
        metadata["relationships_written"] = len(graph_relationships)

        return GraphWriteResult(
            provider=self._safe_provider(normalized_record.provider),
            source_type=normalized_record.source_type,
            raw_record_id=normalized_record.raw_record_id,
            query=normalized_record.query,
            status=FetchStatus.SUCCESS,
            error=None,
            nodes_written=len(graph_nodes),
            relationships_written=len(graph_relationships),
            metadata=metadata,
        )

    def _collect_graph_nodes(
        self,
        normalized_record: NormalizedRecord,
        relationship_result: RelationshipExtractionResult,
    ) -> list[GraphNode] | GraphWriteResult:
        """Build one unique graph node list from normalized and relationship data."""
        nodes_by_key: dict[str, GraphNode] = {}

        for entity in normalized_record.entities:
            graph_node = self._graph_node_from_normalized_entity(
                entity,
                normalized_record.raw_record_id,
                normalized_record.case_id,
            )
            if isinstance(graph_node, GraphWriteResult):
                return graph_node
            nodes_by_key[graph_node.entity_key] = graph_node

        for relationship in relationship_result.relationships:
            from_node = self._graph_node_from_entity_reference(
                relationship.from_entity,
                normalized_record.raw_record_id,
                normalized_record.case_id,
            )
            if isinstance(from_node, GraphWriteResult):
                return from_node
            nodes_by_key[from_node.entity_key] = self._merge_graph_node(
                nodes_by_key.get(from_node.entity_key),
                from_node,
            )

            to_node = self._graph_node_from_entity_reference(
                relationship.to_entity,
                normalized_record.raw_record_id,
                normalized_record.case_id,
            )
            if isinstance(to_node, GraphWriteResult):
                return to_node
            nodes_by_key[to_node.entity_key] = self._merge_graph_node(nodes_by_key.get(to_node.entity_key), to_node)

        return list(nodes_by_key.values())

    def _collect_graph_relationships(
        self,
        relationship_result: RelationshipExtractionResult,
        *,
        case_id: str,
    ) -> list[GraphRelationship] | GraphWriteResult:
        """Build one unique graph relationship list."""
        relationships_by_key: dict[str, GraphRelationship] = {}

        for relationship in relationship_result.relationships:
            graph_relationship = self._graph_relationship_from_extracted_relationship(
                relationship,
                case_id=case_id,
            )
            if isinstance(graph_relationship, GraphWriteResult):
                return graph_relationship
            relationships_by_key[graph_relationship.relationship_key] = self._merge_graph_relationship(
                relationships_by_key.get(graph_relationship.relationship_key),
                graph_relationship,
            )

        return list(relationships_by_key.values())

    def _graph_node_from_normalized_entity(
        self,
        entity: NormalizedEntity,
        raw_record_id: str,
        case_id: str,
    ) -> GraphNode | GraphWriteResult:
        """Turn one normalized entity into one graph node."""
        entity_type = self._canonical_graph_entity_type(entity.entity_type)
        canonical_value = self._canonical_graph_value(entity_type, entity.canonical_value)
        display_value = self._clean_text(entity.display_value) or canonical_value

        if not entity_type or not canonical_value:
            return self._build_graph_entity_error(
                raw_record_id,
                "Normalized entities need entity_type and canonical_value.",
            )

        metadata = dict(entity.metadata)
        metadata["case_id"] = self._clean_case_id(case_id)

        return GraphNode(
            entity_key=self._build_entity_key(entity_type, canonical_value, case_id=case_id),
            entity_type=entity_type,
            canonical_value=canonical_value,
            display_value=display_value,
            metadata=metadata,
        )

    def _graph_node_from_entity_reference(
        self,
        entity_reference: EntityReference,
        raw_record_id: str,
        case_id: str,
    ) -> GraphNode | GraphWriteResult:
        """Turn one relationship endpoint into one graph node."""
        entity_type = self._canonical_graph_entity_type(entity_reference.entity_type)
        canonical_value = self._canonical_graph_value(entity_type, entity_reference.canonical_value)
        display_value = self._clean_text(entity_reference.display_value) or canonical_value

        if not entity_type or not canonical_value:
            return self._build_error_result(
                self._minimal_record(raw_record_id),
                code=ErrorCode.GRAPH_BAD_RELATIONSHIP,
                message="Relationship endpoints need entity_type and canonical_value before graph writes.",
            )

        return GraphNode(
            entity_key=self._build_entity_key(entity_type, canonical_value, case_id=case_id),
            entity_type=entity_type,
            canonical_value=canonical_value,
            display_value=display_value,
            metadata={"case_id": self._clean_case_id(case_id)},
        )

    def _graph_relationship_from_extracted_relationship(
        self,
        relationship: ExtractedRelationship,
        *,
        case_id: str,
    ) -> GraphRelationship | GraphWriteResult:
        """Turn one extracted relationship into one graph edge."""
        relationship_type = self._clean_text(relationship.relationship_type)
        from_type = self._canonical_graph_entity_type(relationship.from_entity.entity_type)
        from_value = self._canonical_graph_value(from_type, relationship.from_entity.canonical_value)
        to_type = self._canonical_graph_entity_type(relationship.to_entity.entity_type)
        to_value = self._canonical_graph_value(to_type, relationship.to_entity.canonical_value)

        if not relationship_type or not from_type or not from_value or not to_type or not to_value:
            return self._build_error_result(
                self._minimal_record(relationship.evidence_record_id),
                code=ErrorCode.GRAPH_BAD_RELATIONSHIP,
                message="Relationships need type and both endpoints before graph writes.",
            )

        from_entity_key = self._build_entity_key(from_type, from_value, case_id=case_id)
        to_entity_key = self._build_entity_key(to_type, to_value, case_id=case_id)
        relationship_key = f"{relationship_type}|{from_entity_key}|{to_entity_key}"
        metadata = dict(relationship.metadata)
        metadata["case_id"] = self._clean_case_id(case_id)

        return GraphRelationship(
            relationship_key=relationship_key,
            relationship_type=relationship_type,
            from_entity_key=from_entity_key,
            to_entity_key=to_entity_key,
            confidence_percent=relationship.confidence_percent,
            evidence_record_id=relationship.evidence_record_id,
            metadata=metadata,
        )

    def _merge_graph_node(self, existing_node: GraphNode | None, new_node: GraphNode) -> GraphNode:
        """Prefer the richest readable node when duplicates point to the same key."""
        if existing_node is None:
            return new_node

        display_value = existing_node.display_value or new_node.display_value
        metadata = dict(existing_node.metadata)
        metadata.update(new_node.metadata)

        return GraphNode(
            entity_key=existing_node.entity_key,
            entity_type=existing_node.entity_type,
            canonical_value=existing_node.canonical_value,
            display_value=display_value,
            metadata=metadata,
        )

    def _merge_graph_relationship(
        self,
        existing_relationship: GraphRelationship | None,
        new_relationship: GraphRelationship,
    ) -> GraphRelationship:
        """Keep the strongest duplicate edge when the same semantic edge appears twice."""
        if existing_relationship is None:
            return new_relationship

        confidence_percent = max(existing_relationship.confidence_percent, new_relationship.confidence_percent)
        metadata = dict(existing_relationship.metadata)
        metadata.update(new_relationship.metadata)

        return GraphRelationship(
            relationship_key=existing_relationship.relationship_key,
            relationship_type=existing_relationship.relationship_type,
            from_entity_key=existing_relationship.from_entity_key,
            to_entity_key=existing_relationship.to_entity_key,
            confidence_percent=confidence_percent,
            evidence_record_id=existing_relationship.evidence_record_id or new_relationship.evidence_record_id,
            metadata=metadata,
        )

    def _build_graph_entity_error(self, raw_record_id: str, message: str) -> GraphWriteResult:
        """Return one graph entity validation error."""
        return self._build_error_result(
            self._minimal_record(raw_record_id),
            code=ErrorCode.GRAPH_BAD_ENTITY,
            message=message,
        )

    def _build_passthrough_result(self, normalized_record: NormalizedRecord) -> GraphWriteResult:
        """Return the upstream normalized status untouched."""
        return GraphWriteResult(
            provider=self._safe_provider(normalized_record.provider),
            source_type=normalized_record.source_type,
            raw_record_id=normalized_record.raw_record_id,
            query=normalized_record.query,
            status=normalized_record.status,
            error=normalized_record.error,
            nodes_written=0,
            relationships_written=0,
            metadata=dict(normalized_record.metadata),
        )

    def _build_error_result(
        self,
        normalized_record: NormalizedRecord,
        *,
        code: ErrorCode,
        message: str,
    ) -> GraphWriteResult:
        """Return one graph-layer error result."""
        metadata = dict(normalized_record.metadata)
        metadata["requested_provider"] = self._provider_text(normalized_record.provider)

        return GraphWriteResult(
            provider=self._safe_provider(normalized_record.provider),
            source_type=normalized_record.source_type,
            raw_record_id=normalized_record.raw_record_id,
            query=normalized_record.query,
            status=FetchStatus.ERROR,
            error=ProviderError(code=code.value, message=message),
            nodes_written=0,
            relationships_written=0,
            metadata=metadata,
        )

    def _minimal_record(self, raw_record_id: str) -> NormalizedRecord:
        """Build a tiny helper record for internal error reporting."""
        return NormalizedRecord(
            provider=ProviderKind.IPINFO,
            source_type=normalized_record_source_type_fallback(),
            case_id="default",
            raw_record_id=raw_record_id,
            query=None,
            status=FetchStatus.SUCCESS,
            normalized_data=None,
            metadata={},
        )

    def _build_entity_key(self, entity_type: str, canonical_value: str, *, case_id: str) -> str:
        """Build one stable node key."""
        return f"case:{self._slugify(self._clean_case_id(case_id))}:{entity_type}:{self._slugify(canonical_value)}"

    def _slugify(self, value: str) -> str:
        """Turn a readable value into a key-safe value."""
        lowered_value = value.strip().lower()
        pieces: list[str] = []

        for character in lowered_value:
            if character.isalnum():
                pieces.append(character)
                continue

            if pieces and pieces[-1] != "-":
                pieces.append("-")

        slug_value = "".join(pieces).strip("-")
        if not slug_value:
            return "unknown"

        return slug_value

    def _clean_text(self, value: Any) -> str:
        """Return one clean string from enums or plain text."""
        if value is None:
            return ""

        if hasattr(value, "value"):
            value = value.value

        if not isinstance(value, str):
            return ""

        return value.strip()

    def _clean_case_id(self, value: Any) -> str:
        """Return a safe case id."""
        cleaned_value = self._clean_text(value)
        if not cleaned_value:
            return "default"

        return cleaned_value

    def _canonical_graph_entity_type(self, value: Any) -> str:
        """Collapse near-duplicate entity labels into one graph label."""
        entity_type = self._clean_text(value).lower()
        if entity_type == "company":
            return "organization"

        if entity_type == "location":
            return "place"

        return entity_type

    def _canonical_graph_value(self, entity_type: str, value: Any) -> str:
        """Normalize canonical values a little more at the graph boundary."""
        cleaned_value = self._clean_text(value)
        if not cleaned_value:
            return ""

        if entity_type == "organization":
            normalized_value = normalize_company_canonical(cleaned_value)
            if normalized_value:
                return normalized_value

        return cleaned_value

    def _safe_provider(self, provider: object) -> ProviderKind:
        """Return a safe provider enum for output records."""
        if isinstance(provider, ProviderKind):
            return provider

        return ProviderKind.IPINFO

    def _provider_text(self, provider: object) -> str:
        """Return a readable provider string for metadata."""
        if hasattr(provider, "value"):
            provider = provider.value

        if not isinstance(provider, str):
            return ""

        return provider.strip()


def normalized_record_source_type_fallback():
    """Return a safe fallback source type without importing more than needed."""
    from backend.schemas.ingestion import SourceKind

    return SourceKind.API
