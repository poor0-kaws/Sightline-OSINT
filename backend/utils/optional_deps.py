"""Tiny fallback objects so the scaffold can import before dependencies are installed."""

# `Any` gives us a broad fallback type when real libraries are missing.
from typing import Any
# `Callable` describes decorator functions in the placeholder classes.
from typing import Callable


class _RouteContainer:
    """Small placeholder that mimics a router enough for skeleton code."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.routes: list[dict[str, Any]] = []
        self.args = args
        self.kwargs = kwargs

    def _register(self, method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append({"method": method, "path": path, "name": func.__name__})
            return func

        return decorator

    def get(self, path: str, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("GET", path)

    def post(self, path: str, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("POST", path)

    def put(self, path: str, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("PUT", path)

    def delete(self, path: str, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self._register("DELETE", path)

    def include_router(self, router: "_RouteContainer", *args: Any, **kwargs: Any) -> None:
        self.routes.extend(getattr(router, "routes", []))


class APIRouter(_RouteContainer):
    """Placeholder for FastAPI's APIRouter."""


class FastAPI(_RouteContainer):
    """Placeholder for FastAPI's app object."""


class HTTPException(Exception):
    """Placeholder for FastAPI's HTTPException."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def Depends(dependency: Callable[..., Any]) -> Callable[..., Any]:
    """Return the dependency unchanged in fallback mode."""
    return dependency


class BaseModel:
    """Very small Pydantic-like model for scaffold use."""

    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def model_dump(self) -> dict[str, Any]:
        return self.__dict__.copy()


def Field(
    default: Any = None,
    *,
    default_factory: Callable[[], Any] | None = None,
    description: str = "",
) -> Any:
    """Return a default value in fallback mode."""
    if default_factory is not None:
        return default_factory()

    return default


class Celery:
    """Placeholder for the Celery app."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs

    def task(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator


class BeautifulSoup:
    """Placeholder for Beautiful Soup."""

    def __init__(self, html: str, parser: str) -> None:
        self.html = html
        self.parser = parser


class AsyncClient:
    """Placeholder for HTTPX AsyncClient."""

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    async def get(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "stub"}

    async def post(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "stub"}


class GraphDatabase:
    """Placeholder for the Neo4j GraphDatabase helper."""

    @staticmethod
    def driver(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "stub-driver"}


class Dedupe:
    """Placeholder for the dedupe matcher."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


FASTAPI_AVAILABLE = False
PYDANTIC_AVAILABLE = False
CELERY_AVAILABLE = False
HTTPX_AVAILABLE = False
BS4_AVAILABLE = False
NEO4J_AVAILABLE = False
DEDUPE_AVAILABLE = False

try:
    # `FastAPI` builds the API app and routers when the real dependency exists.
    from fastapi import APIRouter as RealAPIRouter
    # `Depends` wires route functions to shared service objects.
    from fastapi import Depends as RealDepends
    # `FastAPI` is the actual web application class.
    from fastapi import FastAPI as RealFastAPI
    # `HTTPException` gives standard HTTP error responses.
    from fastapi import HTTPException as RealHTTPException

    APIRouter = RealAPIRouter
    Depends = RealDepends
    FastAPI = RealFastAPI
    HTTPException = RealHTTPException
    FASTAPI_AVAILABLE = True
except ImportError:
    pass

try:
    # `BaseModel` is Pydantic's main schema model.
    from pydantic import BaseModel as RealBaseModel
    # `Field` adds default metadata to Pydantic fields.
    from pydantic import Field as RealField

    BaseModel = RealBaseModel
    Field = RealField
    PYDANTIC_AVAILABLE = True
except ImportError:
    pass

try:
    # `Celery` is the real task queue app when installed.
    from celery import Celery as RealCelery

    Celery = RealCelery
    CELERY_AVAILABLE = True
except ImportError:
    pass

try:
    # `AsyncClient` performs async HTTP requests for API ingestion.
    from httpx import AsyncClient as RealAsyncClient

    AsyncClient = RealAsyncClient
    HTTPX_AVAILABLE = True
except ImportError:
    pass

try:
    # `BeautifulSoup` parses scraped HTML into a tree you can inspect.
    from bs4 import BeautifulSoup as RealBeautifulSoup

    BeautifulSoup = RealBeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    pass

try:
    # `GraphDatabase` creates Neo4j drivers and sessions.
    from neo4j import GraphDatabase as RealGraphDatabase

    GraphDatabase = RealGraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    pass

try:
    # `Dedupe` is the real matching engine for entity resolution work.
    from dedupe import Dedupe as RealDedupe

    Dedupe = RealDedupe
    DEDUPE_AVAILABLE = True
except ImportError:
    pass

