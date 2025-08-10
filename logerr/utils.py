"""
Essential utility functions for core logerr functionality.

This module provides the core utility functions needed for basic Option and Result
operations. For advanced utilities, see logerr.recipes.utilities
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from loguru import logger

from .config import get_log_level, should_log
from .option import Nothing, Some
from .result import Err, Ok

T = TypeVar("T")


def execute[T](
    f: Callable[[], T],
    *,
    on_exception: Literal["option", "result"] = "result",
    default_error: Any = None,
) -> Any:  # Option[T] | Result[T, Exception]
    """Safely execute a callable, wrapping result in Option or Result.

    This eliminates the common pattern of try/catch blocks when creating
    Options or Results from potentially failing operations.

    Args:
        f: The callable to execute safely
        on_exception: Whether to return Option (None) or Result (Err) on exception
        default_error: Default error value if exception occurs

    Returns:
        Option[T] or Result[T, Exception] depending on on_exception parameter

    Examples:
        >>> result = execute(lambda: int("42"))
        >>> result.is_ok()
        True
        >>> result.unwrap()
        42
    """

    try:
        result = f()
        if on_exception == "option":
            return (
                Some(result)
                if result is not None
                else Nothing.from_none("Callable returned None")
            )
        else:
            return Ok(result)
    except Exception as e:
        if on_exception == "option":
            return Nothing.from_exception(e)
        else:
            return Err.from_exception(default_error or e)


def nullable(
    value: T | None,
    *,
    error_factory: Callable[[], Any] | Any | None = None,
    return_type: Literal["option", "result"] = "option",
    log_absence: bool = True,
) -> Any:  # Option[T] | Result[T, Any]
    """Handle nullable values with configurable error strategies.

    Standardizes the common pattern of converting None values to appropriate
    Option or Result types with consistent error handling and logging.

    Args:
        value: The potentially None value to handle
        error_factory: Callable to create error, or error value directly
        return_type: Whether to return Option or Result type
        log_absence: Whether to log when value is None

    Returns:
        Option[T] or Result[T, Any] depending on return_type parameter

    Examples:
        >>> result = nullable("value")
        >>> result.is_some()
        True
        >>> result.unwrap()
        'value'
    """

    if value is not None:
        return Some(value) if return_type == "option" else Ok(value)

    # Handle None case
    if return_type == "option":
        reason = "Value was None"
        if log_absence:
            return Nothing.from_none(reason)
        else:
            return Nothing(reason, _skip_logging=True)
    else:
        if error_factory is None:
            error = ValueError("Value was None")
        elif callable(error_factory):
            error = error_factory()  # type: ignore
        else:
            error = error_factory  # type: ignore
        return Err.from_value(error)


def log(
    message: str,
    *,
    log_level: str = "ERROR",
    extra_context: dict[str, Any] | None = None,
    frame_offset: int = 2,
) -> None:
    """Log a message with basic context from calling frame.

    Provides simple logging functionality for core Option/Result operations.
    For advanced logging with per-library configuration, see logerr.recipes.config

    Args:
        message: The message to log
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        extra_context: Additional context to include in log
        frame_offset: How many frames up the stack to inspect

    Examples:
        >>> log("Operation failed", log_level="WARNING")  # doctest: +SKIP
        >>> log("Value was None", extra_context={"value": None})  # doctest: +SKIP
    """
    # Check if logging is enabled
    if not should_log():
        return

    # Get caller frame for basic context extraction
    frame = sys._getframe(frame_offset)

    # Extract basic context information
    filename = frame.f_code.co_filename
    function_name = frame.f_code.co_name
    line_number = frame.f_lineno

    # Create context dictionary with basic info
    context: dict[str, Any] = {
        "function": function_name,
        "file": os.path.basename(filename),
        "line": str(line_number),
    }

    # Add any extra context provided
    if extra_context:
        context.update(extra_context)

    # Get the appropriate log level
    effective_level = get_log_level()
    actual_level = (
        log_level
        if log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        else effective_level
    )

    # Log with context
    logger.bind(**context).log(actual_level, message)
