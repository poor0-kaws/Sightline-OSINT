"""Tests for connector shells."""

# `build_source_preview` returns a small example of a source's raw data.
from backend.connectors import build_source_preview
# `list_source_definitions` returns the supported source catalog.
from backend.connectors import list_source_definitions
from backend.schemas.ingestion import SourceKind


def test_source_catalog_contains_all_architecture_source_types() -> None:
    """The source catalog should match the architecture data source list."""
    definitions = list_source_definitions()
    actual_kinds = {definition.source_kind for definition in definitions}

    assert actual_kinds == {
        SourceKind.API,
        SourceKind.CSV,
        SourceKind.SCRAPER,
        SourceKind.WEBHOOK,
        SourceKind.MANUAL,
    }


def test_api_source_preview_contains_raw_json_like_data() -> None:
    """API sources should preview raw response-shaped data."""
    preview = build_source_preview(SourceKind.API)

    assert preview.source_kind == SourceKind.API
    assert len(preview.raw_records) == 1
    assert "response_body" in preview.raw_records[0]


def test_manual_source_preview_contains_analyst_entered_note() -> None:
    """Manual input should look like a hand-entered record."""
    preview = build_source_preview(SourceKind.MANUAL)

    assert preview.source_kind == SourceKind.MANUAL
    assert preview.raw_records[0]["entered_by"] == "analyst"
    assert "note" in preview.raw_records[0]
