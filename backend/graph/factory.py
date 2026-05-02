"""Factory for the configured graph repository."""

from __future__ import annotations

from typing import Any

from backend.graph.repository import GraphRepositoryProtocol
from backend.graph.repository import InMemoryGraphRepository
from backend.graph.repository import Neo4jGraphRepository
from backend.settings import Settings


def build_graph_repository(settings: Settings) -> GraphRepositoryProtocol:
    """Build the graph repository selected by settings."""
    if settings.graph_repository_kind == "memory":
        return InMemoryGraphRepository()

    if settings.graph_repository_kind == "neo4j":
        return Neo4jGraphRepository(_build_neo4j_driver(settings))

    raise ValueError("GRAPH_REPOSITORY_KIND must be memory or neo4j.")


def _build_neo4j_driver(settings: Settings) -> Any:
    """Create a Neo4j driver only when the optional dependency is installed."""
    try:
        from neo4j import GraphDatabase
    except ImportError as error:
        raise RuntimeError("The neo4j package is required when GRAPH_REPOSITORY_KIND=neo4j.") from error

    auth = None
    if settings.neo4j_username or settings.neo4j_password:
        auth = (settings.neo4j_username, settings.neo4j_password)

    return GraphDatabase.driver(settings.neo4j_url, auth=auth)
