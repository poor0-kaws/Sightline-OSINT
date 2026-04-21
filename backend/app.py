"""FastAPI app factory shell."""

# `get_settings` loads simple project config.
from backend.config import get_settings
# `router` is the combined API surface.
from backend.api.router import router
# `FastAPI` is the application object or a fallback placeholder.
from backend.utils.optional_deps import FastAPI


# We use an app factory so configuration stays easy to swap in tests or scripts.
def create_app() -> FastAPI:
    """Create the API application shell."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(router)
    return app


app = create_app()

