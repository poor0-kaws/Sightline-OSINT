"""Simple entry point for the current project skeleton."""

from __future__ import annotations

from backend.settings import get_settings


def build_startup_message() -> str:
    """Return a short summary of the current app state."""
    settings = get_settings()

    return (
        f"{settings.app_name} is set up in {settings.app_env} mode. "
        "The current codebase contains the ingestion prototype, not the full API or UI yet."
    )


def main() -> None:
    """Print a small startup message for manual runs."""
    print(build_startup_message())


if __name__ == "__main__":
    main()
