"""Tiny fallback objects so the source-layer code can import cleanly."""

from typing import Any
from typing import Callable


class BaseModel:
    """Very small Pydantic-like model for fallback mode."""

    def __init__(self, **data: Any) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def model_dump(self) -> dict[str, Any]:
        """Return model data as a plain dictionary."""
        return self.__dict__.copy()


def Field(
    default: Any = None,
    *,
    default_factory: Callable[[], Any] | None = None,
    description: str = "",
) -> Any:
    """Return a default value in fallback mode."""
    _ = description

    if default_factory is not None:
        return default_factory()

    return default


PYDANTIC_AVAILABLE = False

try:
    from pydantic import BaseModel as RealBaseModel
    from pydantic import Field as RealField

    BaseModel = RealBaseModel
    Field = RealField
    PYDANTIC_AVAILABLE = True
except ImportError:
    pass
