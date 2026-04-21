"""Small source registry for ingestion connectors."""

# `BaseConnector` is the shared connector parent.
from backend.connectors.base import BaseConnector
from backend.connectors.api_connector import APIConnector
from backend.connectors.csv_connector import CSVConnector
from backend.connectors.manual_connector import ManualConnector
from backend.connectors.scraper_connector import ScraperConnector
from backend.connectors.webhook_connector import WebhookConnector
from backend.schemas.ingestion import IngestionSourceConfig
from backend.schemas.ingestion import SourceDefinition
from backend.schemas.ingestion import SourceKind
from backend.schemas.ingestion import SourcePreview


CONNECTOR_BY_KIND: dict[SourceKind, type[BaseConnector]] = {
    SourceKind.API: APIConnector,
    SourceKind.CSV: CSVConnector,
    SourceKind.SCRAPER: ScraperConnector,
    SourceKind.WEBHOOK: WebhookConnector,
    SourceKind.MANUAL: ManualConnector,
}


def build_default_source_config(source_kind: SourceKind) -> IngestionSourceConfig:
    """Return a readable demo config for one source kind."""
    connector_class = CONNECTOR_BY_KIND[source_kind]
    return IngestionSourceConfig(
        source_id=f"{source_kind.value}-demo",
        source_kind=source_kind,
        location=connector_class.example_location,
        display_name=connector_class.label,
    )


def create_connector(source_config: IngestionSourceConfig) -> BaseConnector:
    """Create the right connector for one source config."""
    connector_class = CONNECTOR_BY_KIND[source_config.source_kind]
    return connector_class(source_config)


def list_source_definitions() -> list[SourceDefinition]:
    """Return human-friendly descriptions of every supported source."""
    definitions: list[SourceDefinition] = []

    for source_kind in SourceKind:
        connector = create_connector(build_default_source_config(source_kind))
        definitions.append(connector.describe_source())

    return definitions


def build_source_preview(source_kind: SourceKind) -> SourcePreview:
    """Return a raw preview for one supported source."""
    connector = create_connector(build_default_source_config(source_kind))
    return connector.build_preview()
