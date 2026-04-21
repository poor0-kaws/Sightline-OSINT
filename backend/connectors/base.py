"""Base connector interface."""

# `ABC` lets us define a shared shape for all connector classes.
from abc import ABC
# `abstractmethod` marks methods that each connector must provide later.
from abc import abstractmethod

# `IngestionSourceConfig` describes what a source looks like.
from backend.schemas.ingestion import IngestionSourceConfig


# We use classes here because each connector needs its own source config and setup state.
class BaseConnector(ABC):
    """Shared base for ingestion connectors."""

    def __init__(self, source_config: IngestionSourceConfig) -> None:
        self.source_config = source_config

    @abstractmethod
    async def fetch_raw_records(self) -> list[dict]:
        """Fetch source records before normalization."""
        raise NotImplementedError("TODO [CORE]: implement source-specific fetch behavior")

    @abstractmethod
    async def normalize_records(self) -> list[dict]:
        """Turn raw source records into a shared record shape."""
        raise NotImplementedError("TODO [CORE]: map raw source data into normalized records")

