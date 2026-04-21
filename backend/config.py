"""Project settings loaded in the simplest readable way."""

# `dataclass` makes a tiny settings object without hidden behavior.
from dataclasses import dataclass
# `os` lets us read environment variables when you later wire real infrastructure.
import os


# We use a dataclass because it is easy to read and easy to swap later.
@dataclass(slots=True)
class Settings:
    """Small container for project settings."""

    app_name: str = "SightlineOSINT"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    redis_url: str = "redis://localhost:6379/0"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"


def get_settings() -> Settings:
    """Build a settings object from environment variables."""
    return Settings(
        app_name=os.getenv("SIGHTLINE_APP_NAME", "SightlineOSINT"),
        app_env=os.getenv("SIGHTLINE_APP_ENV", "development"),
        api_host=os.getenv("SIGHTLINE_API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("SIGHTLINE_API_PORT", "8000")),
        redis_url=os.getenv("SIGHTLINE_REDIS_URL", "redis://localhost:6379/0"),
        neo4j_url=os.getenv("SIGHTLINE_NEO4J_URL", "bolt://localhost:7687"),
        neo4j_user=os.getenv("SIGHTLINE_NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("SIGHTLINE_NEO4J_PASSWORD", "password"),
    )

