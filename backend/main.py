"""HTTP entry point for the current backend prototype."""

from __future__ import annotations

from backend.api import build_app
from backend.settings import get_validated_settings


app = build_app()


def build_startup_message() -> str:
    """Return a short summary of the current app state."""
    settings = get_validated_settings()

    return (
        f"{settings.app_name} is set up in {settings.app_env} mode. "
        "The backend now exposes a small HTTP API for providers, raw records, normalization, and relationships."
    )


def main() -> None:
    """Print a small startup message for manual runs."""
    print(build_startup_message())


if __name__ == "__main__":
    main()
