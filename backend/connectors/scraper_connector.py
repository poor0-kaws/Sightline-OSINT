"""Scraper connector shell."""

# `BaseConnector` gives this connector a shared interface.
from backend.connectors.base import BaseConnector
from backend.schemas.ingestion import SourceKind


class ScraperConnector(BaseConnector):
    """Connector for raw web page scraping."""

    source_kind = SourceKind.SCRAPER
    label = "Web Scraper"
    description = "Downloads web pages and keeps the raw HTML for later parsing."
    example_location = "https://example.com/about"
    raw_shape_summary = "HTML pages plus simple page metadata"

    def get_preview_raw_records(self) -> list[dict]:
        """Return a simple example of raw scraped page data."""
        return [
            {
                "record_id": f"{self.source_config.source_id}-page-1",
                "page_url": self.source_config.location,
                "status_code": 200,
                "html": "<html><body><h1>Example Company</h1><p>Contact hello@example.com</p></body></html>",
            }
        ]
