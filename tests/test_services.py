"""Tests for service shells."""

# `IngestionService` owns source-listing behavior.
from backend.services.ingestion_service import IngestionService
from backend.schemas.ingestion import SourceKind


def test_ingestion_service_lists_manual_source_kind() -> None:
    """The service should expose the full source list, including manual input."""
    service = IngestionService()

    assert service.list_supported_source_types() == [
        SourceKind.API.value,
        SourceKind.CSV.value,
        SourceKind.SCRAPER.value,
        SourceKind.WEBHOOK.value,
        SourceKind.MANUAL.value,
    ]


def test_ingestion_service_previews_csv_raw_shape() -> None:
    """The service should show what raw CSV rows look like."""
    service = IngestionService()
    preview = service.preview_payload_shape(SourceKind.CSV)

    assert preview.source_kind == SourceKind.CSV
    assert preview.raw_records[0]["row_number"] == 1
