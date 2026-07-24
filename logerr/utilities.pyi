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

@overload
def validate[T, E](
    value: T,
    predicate: Callable[[T], bool],
    *,
    error_factory: Callable[[T], E] | E,
    return_type: Literal["result"] = "result",
    capture_exceptions: bool = True,
) -> Result[T, E | Exception]:
    """Validate values using predicates with flexible error handling."""
    ...

@overload
def validate[T, E](
    value: T,
    predicate: Callable[[T], bool],
    *,
    error_factory: Callable[[T], E] | E,
    return_type: Literal["option"],
    capture_exceptions: bool = True,
) -> Option[T]:
    """Validate values using predicates with flexible error handling."""
    ...

def resolve[T](
    provided: T | None, default: T, *, validator: Callable[[T], bool] | None = None
) -> T:
    """Resolve parameter values using Option chaining with validation."""
    ...

def chain[T, U, M](
    value: T,
    operation: Callable[[T], U],
    *,
    error_wrapper: Callable[[Exception], M],
    success_wrapper: Callable[[U], M],
) -> M:
    """Execute operations in a chain while safely handling exceptions."""
    ...

def attribute(obj: Any, attr_name: str, default: Any = "unknown") -> Any:
    """Safely get an attribute value with functional error handling."""
    ...

def error(
    value: Any, constraint: str, valid_options: set[Any] | None = None
) -> ValueError:
    """Create a standardized validation error message."""
    ...

def pipe[T](value: T, *functions: Callable[[Any], Any]) -> Any:
    """Apply a series of functions in pipeline fashion."""
    ...

def try_chain[T](*callables: Callable[[], T]) -> Option[T]:
    """Try a series of callables until one succeeds."""
    ...
