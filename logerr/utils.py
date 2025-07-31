"""
Reusable utility functions for functional patterns in logerr.

This module provides common functional patterns used throughout the library,
reducing code duplication and providing consistent APIs for common operations.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from loguru import logger

# These imports work fine at module level
from .option import Nothing, Option, Some
from .result import Err, Ok

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
M = TypeVar("M")


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
    error_factory: Callable[[], E] | E | None = None,
    return_type: Literal["option", "result"] = "option",
    log_absence: bool = True,
) -> Any:  # Option[T] | Result[T, E]
    """Handle nullable values with configurable error strategies.

    Standardizes the common pattern of converting None values to appropriate
    Option or Result types with consistent error handling and logging.

    Args:
        value: The potentially None value to handle
        error_factory: Callable to create error, or error value directly
        return_type: Whether to return Option or Result type
        log_absence: Whether to log when value is None

    Returns:
        Option[T] or Result[T, E] depending on return_type parameter

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


def validate(
    value: T,
    predicate: Callable[[T], bool],
    *,
    error_factory: Callable[[T], E] | E,
    return_type: Literal["option", "result"] = "result",
    capture_exceptions: bool = True,
) -> Any:  # Option[T] | Result[T, E | Exception]
    """Validate values using predicates with flexible error handling.

    Unifies validation logic across Option and Result types, providing
    consistent predicate testing with configurable error strategies.

    Args:
        value: The value to validate
        predicate: Function that tests the value
        error_factory: Callable to create error from value, or error value directly
        return_type: Whether to return Option or Result type
        capture_exceptions: Whether to catch exceptions in predicate execution

    Returns:
        Option[T] or Result[T, E | Exception] depending on return_type

    Examples:
        >>> result = validate(5, lambda x: x > 0, error_factory=ValueError("Not positive"))
        >>> result.is_ok()
        True
        >>> result.unwrap()
        5
    """

    try:
        if predicate(value):
            return Some(value) if return_type == "option" else Ok(value)

        # Predicate failed
        if callable(error_factory):
            error = error_factory(value)  # type: ignore
        else:
            error = error_factory  # type: ignore

        if return_type == "option":
            return Nothing.from_filter(f"Value {value} failed validation")
        else:
            return Err.from_value(error)

    except Exception as e:
        if capture_exceptions:
            if return_type == "option":
                return Nothing.from_exception(e)
            else:
                return Err.from_exception(e)
        else:
            raise


def log(
    message: str,
    *,
    log_level: str = "ERROR",
    extra_context: dict[str, Any] | None = None,
    frame_offset: int = 2,
    library_name: str | None = None,
) -> None:
    """Log a message with captured context from calling frame.

    Centralizes the common pattern of extracting caller context (function name,
    file, line number) and logging with configurable formatting. This eliminates
    the duplicated frame inspection logic found in Option and Result logging.

    Args:
        message: The message to log
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        extra_context: Additional context to include in log
        frame_offset: How many frames up the stack to inspect
        library_name: Library name for config lookup, auto-detected if None

    Examples:
        >>> log("Operation failed", log_level="WARNING")
        >>> log("Value was None", extra_context={"value": None})
    """
    # Import here to avoid circular import during module initialization
    from .config import get_config, get_log_level_for_library, should_log_for_library

    # Get caller frame for context extraction
    frame = sys._getframe(frame_offset)

    # Extract context information
    filename = frame.f_code.co_filename
    function_name = frame.f_code.co_name
    line_number = frame.f_lineno

    # Auto-detect library name from filename if not provided
    if library_name is None:
        library_name = os.path.basename(os.path.dirname(filename))

    # Check if logging is enabled for this library
    if not should_log_for_library(library_name):
        return

    # Get configuration for context capture
    config = get_config()
    context: dict[str, Any] = {}

    if config.capture_function_name:
        context["function"] = function_name
    if config.capture_filename:
        context["file"] = os.path.basename(filename)
    if config.capture_lineno:
        context["line"] = str(line_number)
    if config.capture_locals and frame.f_locals:
        # Only capture non-sensitive locals
        safe_locals = {
            k: v
            for k, v in frame.f_locals.items()
            if not k.startswith("_") and not callable(v)
        }
        context["locals"] = safe_locals

    # Add any extra context provided
    if extra_context:
        context.update(extra_context)

    # Get the appropriate log level for this library
    effective_level = get_log_level_for_library(library_name)
    actual_level = (
        log_level
        if log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        else effective_level
    )

    # Log with context
    logger.bind(**context).log(actual_level, message)


def resolve(
    provided: T | None, default: T, *, validator: Callable[[T], bool] | None = None
) -> T:
    """Resolve parameter values using Option chaining with validation.

    Standardizes the common pattern of resolving function parameters with
    fallback defaults, commonly seen in retry logic and configuration.

    Args:
        provided: The potentially None provided value
        default: The default value to use if provided is None
        validator: Optional function to validate the resolved value

    Returns:
        The resolved value (provided or default)

    Raises:
        ValueError: If validator is provided and validation fails

    Examples:
        >>> resolve(None, 42)
        42
        >>> resolve(10, 42)
        10
    """

    resolved = Option.from_nullable(provided).unwrap_or(default)

    if validator is not None and not validator(resolved):
        raise ValueError(f"Resolved value {resolved} failed validation")

    return resolved


def chain(
    value: T,
    operation: Callable[[T], U],
    *,
    error_wrapper: Callable[[Exception], M],
    success_wrapper: Callable[[U], M],
) -> M:
    """Execute operations in a chain while safely handling exceptions.

    Eliminates the repetitive try/catch blocks found in monadic operations
    like map, and_then, filter across Option and Result types.

    Args:
        value: The input value to transform
        operation: The transformation function to apply
        error_wrapper: Function to wrap exceptions into return type
        success_wrapper: Function to wrap successful results

    Returns:
        Wrapped result using appropriate wrapper function

    Examples:
        >>> from logerr import Some, Nothing
        >>> result = chain(
        ...     "42",
        ...     int,
        ...     error_wrapper=Nothing.from_exception,
        ...     success_wrapper=Some
        ... )
        >>> result.is_some()
        True
    """
    try:
        result = operation(value)
        return success_wrapper(result)
    except Exception as e:
        return error_wrapper(e)


# Convenience functions that combine common patterns
def attribute(obj: Any, attr_name: str, default: Any = "unknown") -> Any:
    """Safely get an attribute value with functional error handling.

    Common pattern used throughout the codebase for accessing attributes
    like __name__ on functions.

    Args:
        obj: Object to get attribute from
        attr_name: Name of attribute to access
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default

    Examples:
        >>> attribute(len, "__name__", "unknown")
        'len'
        >>> attribute(42, "__name__", "unknown")
        'unknown'
    """

    return Option.from_callable(lambda: getattr(obj, attr_name)).unwrap_or(default)  # type: ignore


def error(
    value: Any, constraint: str, valid_options: set[Any] | None = None
) -> ValueError:
    """Create a standardized validation error message.

    Provides consistent error messaging across validation scenarios.

    Args:
        value: The invalid value
        constraint: Description of the constraint that failed
        valid_options: Set of valid options to include in error message

    Returns:
        ValueError with standardized message format

    Examples:
        >>> err = error("INVALID", "log level", {"DEBUG", "INFO", "ERROR"})
        >>> isinstance(err, ValueError)
        True
    """
    if valid_options:
        return ValueError(
            f"Invalid {constraint} '{value}'. Must be one of: {valid_options}"
        )
    else:
        return ValueError(f"Invalid {constraint}: '{value}'")
