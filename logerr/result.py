"""
Result type implementation with automatic logging integration.

Provides Rust-like Result<T, E> types with automatic logging of error cases
through loguru, configurable via confection.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from loguru import logger

from .config import get_config, get_log_level_for_library, should_log_for_library

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


class Result[T, E](ABC):
    """A type that represents either success (Ok) or failure (Err).

    Result<T, E> is similar to Rust's Result type, providing a way to handle
    operations that might fail without using exceptions. When an Err is created,
    it's automatically logged using loguru with configurable log levels and formats.

    Type Parameters:
        T: The type of the success value
        E: The type of the error value

    Examples:
        Basic usage:
        >>> from logerr import Ok, Err
        >>> success = Ok(42)
        >>> success.is_ok()
        True
        >>> success.unwrap()
        42

        >>> failure = Err("something went wrong")
        >>> failure.is_err()
        True
        >>> failure.unwrap_or(0)
        0

        Method chaining:
        >>> result = Ok(5).map(lambda x: x * 2).map(str)
        >>> result.unwrap()
        '10'
    """

    @abstractmethod
    def is_ok(self) -> bool:
        """Check if this Result contains a success value.

        Returns:
            True if this is an Ok result, False if Err.

        Examples:
            >>> Ok(42).is_ok()
            True
            >>> Err("error").is_ok()
            False
        """
        pass

    @abstractmethod
    def is_err(self) -> bool:
        """Check if this Result contains an error value.

        Returns:
            True if this is an Err result, False if Ok.

        Examples:
            >>> Ok(42).is_err()
            False
            >>> Err("error").is_err()
            True
        """
        pass

    @abstractmethod
    def unwrap(self) -> T:
        """Extract the success value, raising an exception if this is an Err.

        Returns:
            The contained Ok value.

        Raises:
            Exception: If this Result is an Err.

        Examples:
            >>> Ok(42).unwrap()
            42
            >>> Err("failed").unwrap()  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            RuntimeError: Called unwrap on Err: failed
        """
        pass

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """Extract the success value or return a default.

        Args:
            default: The value to return if this is an Err.

        Returns:
            The Ok value if present, otherwise the default.

        Examples:
            >>> Ok(42).unwrap_or(0)
            42
            >>> Err("failed").unwrap_or(0)
            0
        """
        pass

    @abstractmethod
    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        """Extract the success value or compute one from the error.

        Args:
            f: Function to compute a value from the error.

        Returns:
            The Ok value if present, otherwise f(error).

        Examples:
            >>> Ok(42).unwrap_or_else(lambda e: len(str(e)))
            42
            >>> Err("failed").unwrap_or_else(lambda e: len(str(e)))
            6
        """
        pass

    @abstractmethod
    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        """Transform the success value if present.

        Args:
            f: Function to transform the Ok value.

        Returns:
            Ok(f(value)) if this is Ok, otherwise the original Err.

        Examples:
            >>> Ok(5).map(lambda x: x * 2)
            Ok(10)
            >>> Err("failed").map(lambda x: x * 2)
            Err('failed')
        """
        pass

    @abstractmethod
    def map_err(self, f: Callable[[E], U]) -> Result[T, U]:
        """Transform the error value if present.

        Args:
            f: Function to transform the Err value.

        Returns:
            Err(f(error)) if this is Err, otherwise the original Ok.

        Examples:
            >>> Ok(42).map_err(str)
            Ok(42)
            >>> Err(404).map_err(str)
            Err('404')
        """
        pass

    @abstractmethod
    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain Result-returning operations (also known as flatmap).

        Args:
            f: Function that takes the Ok value and returns a new Result.

        Returns:
            f(value) if this is Ok, otherwise the original Err.

        Examples:
            >>> def divide(x: int) -> Result[float, str]:
            ...     if x == 0:
            ...         return Err("division by zero")
            ...     return Ok(10.0 / x)
            >>> Ok(2).and_then(divide)
            Ok(5.0)
            >>> Ok(0).and_then(divide)
            Err('division by zero')
        """
        pass

    @abstractmethod
    def or_else(self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        """Chain Result-returning operations on the error case.

        Args:
            f: Function that takes the Err value and returns a new Result.

        Returns:
            The original Ok if this is Ok, otherwise f(error).

        Examples:
            >>> def retry(error: str) -> Result[int, str]:
            ...     return Ok(99) if "retry" in error else Err("permanent failure")
            >>> Ok(42).or_else(retry)
            Ok(42)
            >>> Err("retry needed").or_else(retry)
            Ok(99)

            For simple defaults, consider using or_default():
            >>> Err("failed").or_default(42)
            Ok(42)
        """
        pass

    @abstractmethod
    def or_default(self, default: T) -> Result[T, E]:
        """Return Ok(default) if this is Err, otherwise return this Ok.

        This is a convenience method equivalent to `or_else(lambda _: Ok(default))`.

        Args:
            default: The default value to wrap in Ok if this is Err.

        Returns:
            The original Ok if this is Ok, otherwise Ok(default).

        Examples:
            >>> Ok(42).or_default(99)
            Ok(42)
            >>> Err("failed").or_default(99)
            Ok(99)
        """
        pass

    @classmethod
    def from_callable(cls, f: Callable[[], T]) -> Result[T, Exception]:
        """Create a Result from a callable that might raise an exception."""
        from . import result as result_module

        return result_module.from_callable(f)

    @classmethod
    def from_optional(cls, value: T | None, error: E) -> Result[T, E]:
        """Create a Result from an optional value."""
        from . import result as result_module

        return result_module.from_optional(value, error)

    @classmethod
    def from_predicate(
        cls, value: T, predicate: Callable[[T], bool], error: E
    ) -> Result[T, E]:
        """Create a Result based on whether a predicate is satisfied."""
        from . import result as result_module

        return result_module.from_predicate(value, predicate, error)


class Ok(Result[T, E]):
    """Represents a successful result containing a value.

    Ok is the success variant of Result<T, E>. It wraps a value of type T
    and provides methods to safely access and transform it.

    Args:
        value: The success value to wrap.

    Examples:
        >>> ok = Ok(42)
        >>> ok.is_ok()
        True
        >>> ok.unwrap()
        42

        Chaining operations:
        >>> Ok("hello").map(str.upper).map(len)
        Ok(5)
    """

    def __init__(self, value: T) -> None:
        """Initialize an Ok result with a value.

        Args:
            value: The success value to wrap.
        """
        self._value = value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self._value

    def unwrap_or(self, default: T) -> T:
        return self._value

    def unwrap_err(self) -> E:
        """Extract the error value, raising an exception if this is an Ok.

        Raises:
            RuntimeError: Always, since Ok contains no error.

        Examples:
            >>> ok = Ok(42)
            >>> ok.unwrap_err()  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            RuntimeError: Called unwrap_err on Ok: 42
        """
        raise RuntimeError(f"Called unwrap_err on Ok: {self._value}")

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        return self._value

    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        try:
            return Ok(f(self._value))
        except Exception as e:
            return Err(e)  # type: ignore

    def map_err(self, f: Callable[[E], U]) -> Result[T, U]:
        return Ok(self._value)

    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        try:
            return f(self._value)
        except Exception as e:
            return Err(e)  # type: ignore

    def or_else(self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        return Ok(self._value)

    def or_default(self, default: T) -> Result[T, E]:
        return Ok(self._value)

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ok) and self._value == other._value

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Ok):
            try:
                result = self._value < other._value
                return bool(result)
            except TypeError:
                return NotImplemented
        elif isinstance(other, Err):
            return False  # Ok is always greater than Err
        return NotImplemented

    def __le__(self, other: object) -> bool:
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Ok):
            try:
                result = self._value > other._value
                return bool(result)
            except TypeError:
                return NotImplemented
        elif isinstance(other, Err):
            return True  # Ok is always greater than Err
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        return self.__eq__(other) or self.__gt__(other)


class Err(Result[T, E]):
    """Represents a failed result containing an error.

    Err is the failure variant of Result<T, E>. It wraps an error value of type E
    and automatically logs the error when created (unless logging is disabled).

    Args:
        error: The error value to wrap.
        _skip_logging: Internal parameter to skip automatic logging.

    Examples:
        >>> err = Err("something went wrong")
        >>> err.is_err()
        True
        >>> err.unwrap_or("default")
        'default'

        Error logging happens automatically:
        >>> Err("database connection failed")  # Logs the error
        Err('database connection failed')

        Creating from exceptions:
        >>> try:
        ...     1 / 0
        ... except Exception as e:
        ...     result = Err.from_exception(e)
        >>> result.is_err()
        True
    """

    def __init__(self, error: E, *, _skip_logging: bool = False) -> None:
        """Initialize an Err result with an error value.

        Args:
            error: The error value to wrap.
            _skip_logging: If True, skip automatic error logging.
        """
        self._error = error
        if not _skip_logging:
            self._log_error()

    def _log_error(self) -> None:
        """Log the error using configured logging settings."""
        config = get_config()

        # Check if logging is enabled globally
        if not config.enabled:
            return

        # Get the calling frame to capture context
        frame = inspect.currentframe()
        caller_frame = None
        library_name = "unknown"

        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            # Try to determine library name from the calling module
            if caller_frame.f_code.co_filename:
                # Extract library name from file path
                import os

                filename = caller_frame.f_code.co_filename
                # Simple heuristic: use the parent directory name
                library_name = os.path.basename(os.path.dirname(filename))

        # Check if logging is enabled for this library
        if not should_log_for_library(library_name):
            return

        # Capture context based on configuration
        context: dict[str, Any] = {}
        if config.capture_function_name and caller_frame:
            context["function"] = caller_frame.f_code.co_name
        if config.capture_filename and caller_frame:
            context["file"] = caller_frame.f_code.co_filename
        if config.capture_lineno and caller_frame:
            context["line"] = caller_frame.f_lineno
        if config.capture_locals and caller_frame:
            context["locals"] = {
                k: v for k, v in caller_frame.f_locals.items() if not k.startswith("_")
            }

        # Get log level for this library
        log_level = get_log_level_for_library(library_name).upper()

        # Build log message
        if config.format:
            message = config.format.format(error=self._error, **context)
        else:
            location = f"{context.get('function', '<?>')}:{context.get('line', '?')}"
            message = f"Result error in {location} - {self._error}"

        # Log at the configured level
        logger.log(log_level, message, **context, error=self._error)

    @classmethod
    def from_exception(cls, exception: Exception) -> Err[Any, Exception]:
        """Create an Err from an exception with automatic logging.

        This is the preferred way to create an Err from a caught exception,
        as it ensures proper typing and automatic logging.

        Args:
            exception: The exception to wrap in an Err.

        Returns:
            An Err containing the exception.

        Examples:
            >>> try:
            ...     int("not a number")
            ... except ValueError as e:
            ...     result = Err.from_exception(e)
            >>> result.is_err()
            True
        """
        return Err[Any, Exception](exception)

    @classmethod
    def from_value(cls, error: E) -> Err[T, E]:
        """Create an Err from any error value with automatic logging.

        Args:
            error: The error value to wrap.

        Returns:
            An Err containing the error value.

        Examples:
            >>> error_result = Err.from_value("validation failed")
            >>> error_result.unwrap_or("default")
            'default'
        """
        return cls(error)

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> T:
        if isinstance(self._error, Exception):
            raise self._error
        else:
            raise RuntimeError(f"Called unwrap on Err: {self._error}")

    def unwrap_err(self) -> E:
        """Extract the error value from this Err.

        Returns:
            The contained error value.

        Examples:
            >>> err = Err.from_value("something went wrong")
            >>> err.unwrap_err()
            'something went wrong'
        """
        return self._error

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        try:
            return f(self._error)
        except Exception as e:
            # If the unwrap_or_else function fails, we need to raise an error
            raise RuntimeError(f"unwrap_or_else function failed: {e}") from e

    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        return Err(self._error, _skip_logging=True)

    def map_err(self, f: Callable[[E], U]) -> Result[T, U]:
        try:
            return Err(f(self._error))
        except Exception as e:
            return Err(e)  # type: ignore

    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return Err(self._error, _skip_logging=True)

    def or_else(self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        try:
            return f(self._error)
        except Exception as e:
            return Err(e)  # type: ignore

    def or_default(self, default: T) -> Result[T, E]:
        return Ok(default)

    def __repr__(self) -> str:
        return f"Err({self._error!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Err) and self._error == other._error

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Err):
            try:
                result = self._error < other._error
                return bool(result)
            except TypeError:
                return NotImplemented
        elif isinstance(other, Ok):
            return True  # Err is always less than Ok
        return NotImplemented

    def __le__(self, other: object) -> bool:
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Err):
            try:
                result = self._error > other._error
                return bool(result)
            except TypeError:
                return NotImplemented
        elif isinstance(other, Ok):
            return False  # Err is never greater than Ok
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        return self.__eq__(other) or self.__gt__(other)


# Factory functions for creating Results
def from_callable[T](f: Callable[[], T]) -> Result[T, Exception]:
    """Execute a callable and return Ok(result) or Err(exception).

    This function safely executes a callable that might raise an exception,
    capturing any exceptions and converting them to Err results with automatic logging.

    Args:
        f: A callable that returns a value of type T.

    Returns:
        Ok(result) if the callable succeeds, Err(exception) if it raises.

    Examples:
        Successful execution:
        >>> result = from_callable(lambda: 42)
        >>> result.unwrap()
        42

        Handling exceptions:
        >>> result = from_callable(lambda: 1 / 0)
        >>> result.is_err()
        True
        >>> result.unwrap_or(0)
        0

        With more complex operations:
        >>> import json
        >>> result = from_callable(lambda: json.loads('{"key": "value"}'))
        >>> result.map(lambda d: d["key"]).unwrap_or("not found")
        'value'
    """
    try:
        return Ok(f())
    except Exception as e:
        return Err.from_exception(e)


def from_optional[T, E](value: T | None, error: E) -> Result[T, E]:
    """Convert an Optional value to a Result.

    This function converts a potentially None value into a Result,
    using the provided error value if the input is None.

    Args:
        value: An optional value that might be None.
        error: The error value to use if value is None.

    Returns:
        Ok(value) if value is not None, Err(error) if value is None.

    Examples:
        With a present value:
        >>> result = from_optional("hello", "no value")
        >>> result.unwrap()
        'hello'

        With None:
        >>> result = from_optional(None, "value was None")
        >>> result.unwrap_or("default")
        'default'

        Chaining with dict.get():
        >>> data = {"name": "Alice"}
        >>> result = from_optional(data.get("name"), "name not found")
        >>> result.map(str.upper).unwrap_or("UNKNOWN")
        'ALICE'
    """
    if value is not None:
        return Ok(value)
    else:
        return Err.from_value(error)


def from_predicate(value: T, predicate: Callable[[T], bool], error: E) -> Result[T, E]:
    """Create a Result based on whether a value satisfies a predicate.

    This function tests a value against a predicate function and returns
    Ok(value) if the predicate passes, or Err(error) if it fails or raises
    an exception. When an exception occurs, it's wrapped as the error value.

    Args:
        value: The value to test.
        predicate: Function to test the value against.
        error: The error value to return if predicate fails.

    Returns:
        Ok(value) if predicate(value) is True, Err(error) if predicate is False,
        or Err(exception) if predicate raises an exception.

    Examples:
        Predicate passes:
        >>> result = from_predicate(42, lambda x: x > 30, "too small")
        >>> result.unwrap()
        42

        Predicate fails:
        >>> result = from_predicate(5, lambda x: x > 30, "too small")
        >>> result.unwrap_or(0)
        0

        Predicate raises exception:
        >>> result = from_predicate("text", lambda s: int(s) > 0, "invalid")
        >>> result.is_err()
        True
    """
    try:
        if predicate(value):
            return Ok(value)
        else:
            return Err.from_value(error)
    except Exception as e:
        # Type: ignore because exception handling changes the error type, but this is expected behavior
        return Err.from_exception(e)  # type: ignore[return-value]


def predicate_validator[T, E](
    predicate: Callable[[T], bool], error: E
) -> Callable[[T], Result[T, E]]:
    """Create a reusable predicate validator function.

    This function returns a curried version of from_predicate, allowing you to
    create reusable validation functions that return Results.

    Args:
        predicate: Function to test values against.
        error: The error value to return if predicate fails.

    Returns:
        A function that takes a value and returns a Result.

    Examples:
        Create reusable validators:
        >>> validate_positive = predicate_validator(lambda x: x > 0, "must be positive")
        >>> validate_positive(42).unwrap()
        42
        >>> validate_positive(-5).is_err()
        True

        Use with method chaining:
        >>> email_validator = predicate_validator(lambda s: "@" in s, "invalid email format")
        >>> Ok("user@example.com").and_then(email_validator).is_ok()
        True
    """

    def validator_func(value: T) -> Result[T, E]:
        # Type: ignore because from_predicate might return Exception in error case
        return from_predicate(value, predicate, error)  # type: ignore[return-value]

    return validator_func
