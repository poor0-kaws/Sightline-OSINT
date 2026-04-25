"""Shared test helpers."""

from __future__ import annotations

from collections.abc import Iterator
import os

import pytest

from backend.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    """Make each test read fresh environment values."""
    original_environ = os.environ.copy()
    get_settings.cache_clear()

    yield

    os.environ.clear()
    os.environ.update(original_environ)
    get_settings.cache_clear()
