"""
Utility functions for functional patterns in logerr.

Eliminates code duplication and provides consistent APIs for common
Option/Result patterns: safe execution, nullable handling, validation,
parameter resolution, exception-safe chaining, and simple logging.
"""

from __future__ import annotations

import functools
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, overload

from loguru import logger

from .config import get_log_level, should_log
from .option import Nothing, Option, Some
from .result import Err, Ok, Result


@overload
def execute[T](
    f: Callable[[], T],
    *,
    return_type: Literal["result"] = "result",
    default_error: Any = None,
) -> Result[T, Exception]: ...
@overload
def execute[T](
    f: Callable[[], T],
    *,
    return_type: Literal["option"],
    default_error: Any = None,
) -> Option[T]: ...
def execute[T](
    f: Callable[[], T],
    *,
    return_type: Literal["option", "result"] = "result",
    default_error: Any = None,
) -> Any:  # Option[T] | Result[T, Exception]
    """Safely execute a callable, wrapping result in Option or Result.

    This eliminates the common pattern of try/catch blocks when creating
    Options or Results from potentially failing operations.

    Args:
        f: The callable to execute safely
        return_type: Whether to return Option (None) or Result (Err) on exception
        default_error: Default error value if exception occurs

    Returns:
        Option[T] or Result[T, Exception] depending on return_type parameter

    Examples:
        >>> result = execute(lambda: int("42"))
        >>> result.is_ok()
        True
        >>> result.unwrap()
        42
    """

    try:
        result = f()
        match return_type:
            case "option":
                return (
                    Some(result)
                    if result is not None
                    else Nothing.from_none("Callable returned None")
                )
            case "result":
                return Ok(result)
    except Exception as e:
        match return_type:
            case "option":
                return Nothing.from_exception(e)
            case "result":
                return Err.from_exception(
                    default_error if default_error is not None else e
                )


@overload
def nullable[T](
    value: T | None,
    *,
    error_factory: Callable[[], Any] | Any | None = None,
    return_type: Literal["option"] = "option",
    log_absence: bool = True,
) -> Option[T]: ...
@overload
def nullable[T](
    value: T | None,
    *,
    error_factory: Callable[[], Any] | Any | None = None,
    return_type: Literal["result"],
    log_absence: bool = True,
) -> Result[T, Any]: ...
def nullable[T](
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
        match return_type:
            case "option":
                return Some(value)
            case "result":
                return Ok(value)

    # Handle None case
    match return_type:
        case "option":
            reason = "Value was None"
            if log_absence:
                return Nothing.from_none(reason)
            else:
                return Nothing(reason, _skip_logging=True)
        case "result":
            match error_factory:
                case None:
                    error = ValueError("Value was None")
                case _ if callable(error_factory):
                    error = error_factory()  # type: ignore
                case _:
                    error = error_factory  # type: ignore
            if log_absence:
                return Err.from_value(error)
            else:
                return Err(error, _skip_logging=True)


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
        "file": Path(filename).name,
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


@overload
def validate[T, E](
    value: T,
    predicate: Callable[[T], bool],
    *,
    error_factory: Callable[[T], E] | E,
    return_type: Literal["result"] = "result",
    capture_exceptions: bool = True,
) -> Result[T, E | Exception]: ...
@overload
def validate[T, E](
    value: T,
    predicate: Callable[[T], bool],
    *,
    error_factory: Callable[[T], E] | E,
    return_type: Literal["option"],
    capture_exceptions: bool = True,
) -> Option[T]: ...
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
        error = (
            error_factory(value)  # type: ignore
            if callable(error_factory)
            else error_factory  # type: ignore
        )

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
    like map, then, filter across Option and Result types. Useful when you
    want the old catch-and-convert behavior that map()/then()/filter() no
    longer provide directly (they propagate exceptions to match Rust
    semantics - see CHANGELOG).

    Args:
        value: The input value to transform
        operation: The transformation function to apply
        error_wrapper: Function to wrap exceptions into return type
        success_wrapper: Function to wrap successful results

    Returns:
        Wrapped result using appropriate wrapper function

    Examples:
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
def pipe[T](value: T, *functions: Callable[[Any], Any]) -> Result[Any, Exception]:
    """Apply a series of functions in pipeline fashion, short-circuiting on failure.

    Enables clean functional composition without deep nesting. Each function is
    applied via Result.of(), so if any step raises, the exception is caught and
    returned as Err immediately - remaining functions are not called.

    Args:
        value: Initial value to transform
        *functions: Functions to apply in sequence

    Returns:
        Ok(final_result) if every step succeeded, otherwise Err(exception) from
        the first step that raised.

    Examples:
        >>> from logerr.utilities import pipe
        >>> result = pipe(
        ...     "  hello world  ",
        ...     str.strip,
        ...     str.upper,
        ...     lambda s: s.split()
        ... )
        >>> result.unwrap()
        ['HELLO', 'WORLD']
    """
    result = value
    for func in functions:
        step = Result.of(lambda f=func, r=result: f(r))
        if step.is_err():
            return step
        result = step.unwrap()
    return Ok(result)


def try_chain[T](*callables: Callable[[], T]) -> Option[T]:
    """Try a series of callables until one succeeds.

    Useful for fallback patterns where you want to try multiple approaches.

    Args:
        *callables: Functions to try in order

    Returns:
        Some(result) from first successful callable, Nothing if all fail

    Examples:
        >>> from logerr.utilities import try_chain
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


def wrap_result[T, E](
    func: Callable[..., T | Result[T, E]],
) -> Callable[..., Result[T, E]]:
    """Decorate a function so exceptions and return values both become a Result.

    Eliminates the common try/except-then-return-Err boilerplate around a
    function body that mixes ordinary code with Result-returning calls:
    - Returns a Result already? Passed through unchanged - no unwrap_err()
      then re-wrap needed.
    - Returns a plain value? Wrapped as Ok(value). This includes None - a
      None return is wrapped as Ok(None), not treated as an error (contrast
      with wrap_option(), where a None return becomes Nothing).
    - Raises? Caught and converted to Err(exception), auto-logged the same
      way Result.of() already logs (via Err's own constructor).

    Note:
        wrap_result and wrap_option are not interchangeable. Decorating a
        function whose return type doesn't match the decorator (e.g.
        @wrap_option on a function that returns a Result) does not raise or
        warn - it just wraps that return value as the success case, e.g.
        @wrap_option on a Result-returning function gives Some(Ok(...)),
        and @wrap_result on an Option-returning function gives Ok(Nothing(...)).
        Pick the decorator that matches the function's actual return type.

    Args:
        func: The function to decorate. May return T or Result[T, E].

    Returns:
        A wrapped function that always returns a Result[T, E].

    Examples:
        >>> @wrap_result
        ... def parse(text: str) -> int:
        ...     return int(text)
        >>> parse("42").unwrap()
        42
        >>> parse("nope").is_err()
        True
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, E]:
        try:
            outcome = func(*args, **kwargs)
        except Exception as e:
            # Type: ignore because exception handling changes the error type,
            # but this is expected behavior (see Result.from_predicate).
            return Err.from_exception(e)  # type: ignore[return-value]
        if isinstance(outcome, Result):
            return outcome
        return Ok(outcome)

    return wrapper


def wrap_option[T](func: Callable[..., T | Option[T]]) -> Callable[..., Option[T]]:
    """Decorate a function so exceptions and return values both become an Option.

    Mirrors wrap_result() for the Option case:
    - Returns an Option already? Passed through unchanged.
    - Returns a non-None plain value? Wrapped as Some(value).
    - Returns None? Converted to Nothing (matching nullable()'s existing
      None-handling, so there's a single None-handling convention).
    - Raises? Caught and converted to Nothing, auto-logged via Nothing's
      own constructor.

    Note:
        wrap_result and wrap_option are not interchangeable. Decorating a
        function whose return type doesn't match the decorator (e.g.
        @wrap_result on a function that returns an Option) does not raise
        or warn - it just wraps that return value as the success case,
        e.g. @wrap_result on an Option-returning function gives
        Ok(Nothing(...)), and @wrap_option on a Result-returning function
        gives Some(Ok(...)). Pick the decorator that matches the
        function's actual return type.

    Args:
        func: The function to decorate. May return T, None, or Option[T].

    Returns:
        A wrapped function that always returns an Option[T].

    Examples:
        >>> @wrap_option
        ... def find(items: list[int], target: int) -> int | None:
        ...     return next((x for x in items if x == target), None)
        >>> find([1, 2, 3], 2).unwrap()
        2
        >>> find([1, 2, 3], 9).is_nothing()
        True
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Option[T]:
        try:
            outcome = func(*args, **kwargs)
        except Exception as e:
            return Nothing.from_exception(e)
        if isinstance(outcome, Option):
            return outcome
        if outcome is None:
            return Nothing.from_none(f"{func.__name__} returned None")
        return Some(outcome)

    return wrapper
