"""Type stubs for logerr.utilities module."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeVar, overload

from .option import Option
from .result import Result

T = TypeVar("T")

@overload
def execute[T](
    f: Callable[[], T],
    *,
    return_type: Literal["result"] = "result",
    default_error: Any = None,
) -> Result[T, Exception]:
    """Safely execute a callable, wrapping result in Option or Result."""
    ...

@overload
def execute[T](
    f: Callable[[], T],
    *,
    return_type: Literal["option"],
    default_error: Any = None,
) -> Option[T]:
    """Safely execute a callable, wrapping result in Option or Result."""
    ...

@overload
def nullable[T](
    value: T | None,
    *,
    error_factory: Callable[[], Any] | Any | None = None,
    return_type: Literal["option"] = "option",
    log_absence: bool = True,
) -> Option[T]:
    """Handle nullable values with configurable error strategies."""
    ...

@overload
def nullable[T](
    value: T | None,
    *,
    error_factory: Callable[[], Any] | Any | None = None,
    return_type: Literal["result"],
    log_absence: bool = True,
) -> Result[T, Any]:
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
