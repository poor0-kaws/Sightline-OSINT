"""Logging setup for the scaffold."""

# `logging` is Python's built-in way to print structured messages.
import logging


def configure_logging() -> None:
    """Set a simple logging format that is easy to skim."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
    )

