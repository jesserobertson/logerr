"""Type stubs for logerr.utils module."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeVar

T = TypeVar("T")

def execute[T](
    f: Callable[[], T],
    *,
    on_exception: Literal["option", "result"] = "result",
    default_error: Any = None,
) -> Any:
    """Safely execute a callable, wrapping result in Option or Result."""
    ...

def nullable[T](
    value: T | None,
    *,
    error_factory: Callable[[], Any] | Any | None = None,
    return_type: Literal["option", "result"] = "option",
    log_absence: bool = True,
) -> Any:
    """Handle nullable values with configurable error strategies."""
    ...

def log(
    message: str,
    *,
    log_level: str = "ERROR",
    extra_context: dict[str, Any] | None = None,
    frame_offset: int = 2,
) -> None:
    """Log a message with basic context from calling frame."""
    ...
