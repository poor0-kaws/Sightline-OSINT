"""Service layer for visible scaffold status."""


# We use plain functions here because the demo status is static and has no hidden state.
class StatusService:
    """Provides simple visible status information."""

    def get_dashboard_snapshot(self) -> dict:
        """Return small demo numbers for a status page or CLI view."""
        return {
            "sources_configured": 0,
            "entities_loaded": 0,
            "graph_links": 0,
            "reports_generated": 0,
            "note": "TODO [OPTIONAL]: connect this to real counters later",
        }

