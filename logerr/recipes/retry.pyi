"""Type stubs for logerr.recipes.retry module."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from ..result import Result

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")

def on_err(
    stop: Any = None,
    wait: Any = None,
    log_attempts: bool = True,
) -> Callable[[Callable[..., Result[T, E]]], Callable[..., Result[T, E]]]:
    """Retry a Result-returning function when it returns Err."""
    ...

def on_err_type(
    *error_types: type[Exception],
    stop: Any = None,
    wait: Any = None,
    log_attempts: bool = True,
) -> Callable[[Callable[..., Result[T, E]]], Callable[..., Result[T, E]]]:
    """Retry only when Result contains specific exception types."""
    ...

def with_retry[T](
    func: Callable[[], T],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    log_attempts: bool = True,
) -> Result[T, Exception]:
    """Execute a function with simple retry logic, returning a Result."""
    ...

def until_ok[T, E](
    func: Callable[[], Result[T, E]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    log_attempts: bool = True,
) -> Result[T, E]:
    """Retry a Result-returning function until it returns Ok."""
    ...

def quick[T](func: Callable[[], T]) -> Result[T, Exception]:
    """Quick retry with 2 attempts and minimal delay."""
    ...

def standard[T](func: Callable[[], T]) -> Result[T, Exception]:
    """Standard retry with exponential backoff."""
    ...

def persistent[T](func: Callable[[], T]) -> Result[T, Exception]:
    """Persistent retry for important operations."""
    ...
