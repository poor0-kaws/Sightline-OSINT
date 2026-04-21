"""Celery app shell."""

# `get_settings` loads queue connection settings.
from backend.config import get_settings
# `Celery` is the task queue app or a safe placeholder.
from backend.utils.optional_deps import Celery


# We keep Celery setup in its own module so workers and API code can share one app object.
def create_celery_app() -> Celery:
    """Create the Celery app shell."""
    settings = get_settings()
    return Celery(
        "sightline_worker",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )


celery_app = create_celery_app()

