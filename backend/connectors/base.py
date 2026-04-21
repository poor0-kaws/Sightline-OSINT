"""Base connector interface."""

# `ABC` lets us define a shared shape for all connector classes.
from abc import ABC
# `abstractmethod` marks methods that each connector must provide later.
from abc import abstractmethod

# `IngestionSourceConfig` describes what a source looks like.
from backend.schemas.ingestion import IngestionSourceConfig
from backend.schemas.ingestion import SourceDefinition
from backend.schemas.ingestion import SourceKind
from backend.schemas.ingestion import SourcePreview


# We use classes here because each connector needs its own source config and setup state.
class BaseConnector(ABC):
    """Shared base for ingestion connectors."""

    source_kind: SourceKind = SourceKind.API
    label: str = "Source"
    description: str = "Generic ingestion source"
    example_location: str = "TODO"
    raw_shape_summary: str = "Raw records"

    def __init__(self, source_config: IngestionSourceConfig) -> None:
        self.source_config = source_config

    def describe_source(self) -> SourceDefinition:
        """Return a plain-English description of this source family."""
        return SourceDefinition(
            source_kind=self.source_kind,
            label=self.label,
            description=self.description,
            example_location=self.example_location,
            raw_shape_summary=self.raw_shape_summary,
        )

    def build_preview(self) -> SourcePreview:
        """Return a small raw-data preview for this source."""
        raw_records = self.get_preview_raw_records()
        return SourcePreview(
            source_kind=self.source_kind,
            source_id=self.source_config.source_id,
            raw_records=raw_records,
            note=f"{self.label} sources start as raw records. Cleaning happens in the next pipeline step.",
        )

    async def fetch_raw_records(self) -> list[dict]:
        """Fetch source records before normalization."""
        return self.get_preview_raw_records()

    @abstractmethod
    def get_preview_raw_records(self) -> list[dict]:
        """Return example raw records for this source family."""
        raise NotImplementedError("Each connector must show the raw records it produces")

    async def normalize_records(self) -> list[dict]:
        """Turn raw source records into a shared record shape."""
        return []
