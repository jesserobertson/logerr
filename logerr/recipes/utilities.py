"""
Advanced utility functions for functional patterns in logerr.

These utilities provide sophisticated patterns that extend beyond the core
Option/Result functionality. For basic utilities, use logerr.utils
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from ..option import Nothing, Option, Some
from ..result import Err, Ok


def validate[T, E](
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


def resolve[T](
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


def chain[T, U, M](
    value: T,
    operation: Callable[[T], U],
    *,
    error_wrapper: Callable[[Exception], M],
    success_wrapper: Callable[[U], M],
) -> M:
    """Execute operations in a chain while safely handling exceptions.

    Eliminates the repetitive try/catch blocks found in monadic operations
    like map, then, filter across Option and Result types.

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

    return Option.of(lambda: getattr(obj, attr_name)).unwrap_or(default)  # type: ignore


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


# Convenience function for pipeline-style functional composition
def pipe[T](value: T, *functions: Callable[[Any], Any]) -> Any:
    """Apply a series of functions in pipeline fashion.

    Enables clean functional composition without deep nesting.

    Args:
        value: Initial value to transform
        *functions: Functions to apply in sequence

    Returns:
        Result of applying all functions in sequence

    Examples:
        >>> from logerr.recipes.utilities import pipe
        >>> result = pipe(
        ...     "  hello world  ",
        ...     str.strip,
        ...     str.upper,
        ...     lambda s: s.split()
        ... )
        >>> result
        ['HELLO', 'WORLD']
    """
    result = value
    for func in functions:
        result = func(result)
    return result


def try_chain[T](*callables: Callable[[], T]) -> Option[T]:
    """Try a series of callables until one succeeds.

    Useful for fallback patterns where you want to try multiple approaches.

    Args:
        *callables: Functions to try in order

    Returns:
        Some(result) from first successful callable, Nothing if all fail

    Examples:
        >>> from logerr.recipes.utilities import try_chain
        >>> result = try_chain(
        ...     lambda: int("invalid"),  # Will fail
        ...     lambda: int("42")        # Will succeed
        ... )
        >>> result.unwrap()
        42
    """
    for callable_func in callables:
        try:
            result = callable_func()
            return Some(result)
        except Exception:
            continue
    return Nothing.from_none("All callables failed")
