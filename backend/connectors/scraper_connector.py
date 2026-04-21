"""Scraper connector shell."""

# `AsyncClient` is the HTTP client used to fetch web pages.
from backend.utils.optional_deps import AsyncClient
# `BeautifulSoup` is the HTML parser used to inspect fetched pages.
from backend.utils.optional_deps import BeautifulSoup

# `BaseConnector` gives this connector a shared interface.
from backend.connectors.base import BaseConnector


# We keep scraping async because page fetches are network-bound.
class ScraperConnector(BaseConnector):
    """Connector shell for HTML scraping."""

    async def fetch_raw_records(self) -> list[dict]:
        """Fetch source pages for later parsing."""
        # TODO [CORE]: download the target pages and capture the raw HTML you care about.
        async with AsyncClient() as client:
            _ = client
            return []

    async def normalize_records(self) -> list[dict]:
        """Extract structured records from fetched HTML."""
        # TODO [CORE]: pick selectors, parse fields, and map results into normalized records.
        _ = BeautifulSoup("<html></html>", "html.parser")
        return []

