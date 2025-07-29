"""
Option type implementation with automatic logging integration.

Provides Rust-like Option<T> types with automatic logging of None cases
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
U = TypeVar("U")


class Option[T](ABC):
    """A type that represents an optional value: either Some(T) or Nothing.

    Option<T> is similar to Rust's Option type, providing a way to handle
    values that might be absent without using None. When a Nothing is created
    (indicating an unexpected absence), it's automatically logged using loguru
    with configurable log levels and formats.

    Type Parameters:
        T: The type of the contained value

    Examples:
        Basic usage:
        >>> from logerr import Some, Nothing
        >>> present = Some(42)
        >>> present.is_some()
        True
        >>> present.unwrap()
        42

        >>> absent = Nothing.empty()  # Use empty() to avoid logging
        >>> absent.is_nothing()
        True
        >>> absent.unwrap_or(0)
        0

        Method chaining:
        >>> option = Some("hello").map(str.upper).filter(lambda s: len(s) > 3)
        >>> option.unwrap()
        'HELLO'
    """

    @abstractmethod
    def is_some(self) -> bool:
        """Check if this Option contains a value.

        Returns:
            True if this is a Some option, False if Nothing.

        Examples:
            >>> Some(42).is_some()
            True
            >>> Nothing.empty().is_some()
            False
        """
        pass

    @abstractmethod
    def is_nothing(self) -> bool:
        """Check if this Option contains no value.

        Returns:
            True if this is a Nothing option, False if Some.

        Examples:
            >>> Some(42).is_nothing()
            False
            >>> Nothing.empty().is_nothing()
            True
        """
        pass

    @abstractmethod
    def unwrap(self) -> T:
        """Extract the contained value, raising an exception if this is Nothing.

        Returns:
            The contained Some value.

        Raises:
            ValueError: If this Option is Nothing.

        Examples:
            >>> Some(42).unwrap()
            42
            >>> Nothing.empty().unwrap()  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            ValueError: Called unwrap on Nothing: Empty option
        """
        pass

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """Extract the contained value or return a default.

        Args:
            default: The value to return if this is Nothing.

        Returns:
            The Some value if present, otherwise the default.

        Examples:
            >>> Some(42).unwrap_or(0)
            42
            >>> Nothing.empty().unwrap_or(0)
            0
        """
        pass

    @abstractmethod
    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        """Extract the contained value or compute one from a closure.

        Args:
            f: Function to compute a value if this is Nothing.

        Returns:
            The Some value if present, otherwise f().

        Examples:
            >>> Some(42).unwrap_or_else(lambda: 0)
            42
            >>> Nothing.empty().unwrap_or_else(lambda: 99)
            99
        """
        pass

    @abstractmethod
    def map(self, f: Callable[[T], U]) -> Option[U]:
        """Transform the contained value if present.

        Args:
            f: Function to transform the Some value.

        Returns:
            Some(f(value)) if this is Some, otherwise Nothing.

        Examples:
            >>> Some(5).map(lambda x: x * 2)
            Some(10)
            >>> Nothing.empty().map(lambda x: x * 2)
            Nothing('Empty option')
        """
        pass

    @abstractmethod
    def and_then(self, f: Callable[[T], Option[U]]) -> Option[U]:
        """Chain Option-returning operations (also known as flatmap).

        Args:
            f: Function that takes the Some value and returns a new Option.

        Returns:
            f(value) if this is Some, otherwise Nothing.

        Examples:
            >>> def safe_divide(x: int) -> Option[float]:
            ...     if x == 0:
            ...         return Nothing.from_filter("division by zero")
            ...     return Some(10.0 / x)
            >>> Some(2).and_then(safe_divide)
            Some(5.0)
            >>> Some(0).and_then(safe_divide)  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass

    @abstractmethod
    def or_else(self, f: Callable[[], Option[T]]) -> Option[T]:
        """Chain Option-returning operations on the Nothing case.

        Args:
            f: Function that returns a new Option if this is Nothing.

        Returns:
            The original Some if this is Some, otherwise f().

        Examples:
            >>> Some(42).or_else(lambda: Some(99))
            Some(42)
            >>> Nothing.empty().or_else(lambda: Some(99))
            Some(99)
        """
        pass

    @abstractmethod
    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        """Keep the value only if it satisfies a predicate.

        Args:
            predicate: Function to test the contained value.

        Returns:
            The original Some if predicate returns True, otherwise Nothing.

        Examples:
            >>> Some(42).filter(lambda x: x > 30)
            Some(42)
            >>> Some(5).filter(lambda x: x > 30)  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass


class Some(Option[T]):
    """Represents an option containing a value.

    Some is the "present" variant of Option<T>. It wraps a value of type T
    and provides methods to safely access and transform it.

    Args:
        value: The value to wrap.

    Examples:
        >>> some = Some(42)
        >>> some.is_some()
        True
        >>> some.unwrap()
        42

        Chaining operations:
        >>> Some("hello").map(str.upper).map(len)
        Some(5)
    """

    def __init__(self, value: T) -> None:
        """Initialize a Some option with a value.

        Args:
            value: The value to wrap.
        """
        self._value = value

    def is_some(self) -> bool:
        return True

    def is_nothing(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self._value

    def unwrap_or(self, default: T) -> T:
        return self._value

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        return self._value

    def map(self, f: Callable[[T], U]) -> Option[U]:
        try:
            result = f(self._value)
            if result is None:
                return Nothing.from_none("Map function returned None")
            return Some(result)
        except Exception as e:
            return Nothing.from_exception(e)

    def and_then(self, f: Callable[[T], Option[U]]) -> Option[U]:
        try:
            return f(self._value)
        except Exception as e:
            return Nothing.from_exception(e)

    def or_else(self, f: Callable[[], Option[T]]) -> Option[T]:
        return self

    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        try:
            if predicate(self._value):
                return self
            else:
                return Nothing.from_filter("Value did not pass filter predicate")
        except Exception as e:
            return Nothing.from_exception(e)

    def __repr__(self) -> str:
        return f"Some({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Some) and self._value == other._value

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Some):
            try:
                result = self._value < other._value
                return bool(result)
            except TypeError:
                return NotImplemented
        elif isinstance(other, Nothing):
            return False  # Some is always greater than Nothing
        return NotImplemented

    def __le__(self, other: object) -> bool:
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Some):
            try:
                result = self._value > other._value
                return bool(result)
            except TypeError:
                return NotImplemented
        elif isinstance(other, Nothing):
            return True  # Some is always greater than Nothing
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        return self.__eq__(other) or self.__gt__(other)


class Nothing(Option[T]):
    """Represents an option with no value.

    Nothing is the "absent" variant of Option<T>. It indicates the absence of a value
    and automatically logs the absence when created (unless logging is disabled).

    Args:
        reason: Description of why the value is absent.
        _skip_logging: Internal parameter to skip automatic logging.

    Examples:
        >>> nothing = Nothing("value not found")
        >>> nothing.is_nothing()
        True
        >>> nothing.unwrap_or("default")
        'default'

        Creating from exceptions:
        >>> try:
        ...     int("not a number")
        ... except ValueError as e:
        ...     option = Nothing.from_exception(e)
        >>> option.is_nothing()
        True

        For normal control flow, use empty():
        >>> Nothing.empty()  # No logging
        Nothing('Empty option')
    """

    def __init__(
        self, reason: str = "No value", *, _skip_logging: bool = False
    ) -> None:
        """Initialize a Nothing option with a reason.

        Args:
            reason: Description of why the value is absent.
            _skip_logging: If True, skip automatic logging.
        """
        self._reason = reason
        if not _skip_logging:
            self._log_nothing()

    def _log_nothing(self) -> None:
        """Log the Nothing case using configured logging settings."""
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

        # Get log level for this library (default to WARNING for Nothing cases)
        log_level = get_log_level_for_library(library_name).upper()
        # For Nothing cases, we might want to use a lower severity by default
        if log_level == "ERROR":
            log_level = "WARNING"

        # Build log message
        if config.format:
            message = config.format.format(reason=self._reason, **context)
        else:
            location = f"{context.get('function', '<?>')}:{context.get('line', '?')}"
            message = f"Option Nothing in {location} - {self._reason}"

        # Log at the configured level
        logger.log(log_level, message, **context, reason=self._reason)

    @classmethod
    def from_exception(cls, exception: Exception) -> Nothing[T]:
        """Create a Nothing from an exception with automatic logging.

        This is the preferred way to create a Nothing from a caught exception,
        as it ensures proper logging and descriptive error messages.

        Args:
            exception: The exception that caused the absence.

        Returns:
            A Nothing containing information about the exception.

        Examples:
            >>> try:
            ...     int("not a number")
            ... except ValueError as e:
            ...     option = Nothing.from_exception(e)
            >>> option.is_nothing()
            True
        """
        return cls(f"Exception: {exception}")

    @classmethod
    def from_none(cls, reason: str = "Value was None") -> Nothing[T]:
        """Create a Nothing from a None value with automatic logging.

        Args:
            reason: Description of why the None was unexpected.

        Returns:
            A Nothing with the given reason.

        Examples:
            >>> option = Nothing.from_none("Database returned None")
            >>> option.unwrap_or("default")
            'default'
        """
        return cls(reason)

    @classmethod
    def from_filter(cls, reason: str = "Filter condition failed") -> Nothing[T]:
        """Create a Nothing from a failed filter predicate with automatic logging.

        Args:
            reason: Description of why the filter failed.

        Returns:
            A Nothing with the given reason.

        Examples:
            >>> option = Nothing.from_filter("Value was too small")
            >>> option.is_nothing()
            True
        """
        return cls(reason)

    @classmethod
    def empty(cls) -> Nothing[T]:
        """Create a Nothing without logging (for normal control flow).

        Use this method when the absence of a value is expected and part of
        normal program flow, so it shouldn't be logged as an error.

        Returns:
            A Nothing that won't trigger automatic logging.

        Examples:
            >>> option = Nothing.empty()
            >>> option.is_nothing()
            True
            >>> option.unwrap_or("default")
            'default'
        """
        return cls("Empty option", _skip_logging=True)

    def is_some(self) -> bool:
        return False

    def is_nothing(self) -> bool:
        return True

    def unwrap(self) -> T:
        raise ValueError(f"Called unwrap on Nothing: {self._reason}")

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        try:
            return f()
        except Exception as e:
            # If the unwrap_or_else function fails, we need to raise an error
            raise ValueError(f"unwrap_or_else function failed: {e}") from e

    def map(self, f: Callable[[T], U]) -> Option[U]:
        return Nothing(self._reason, _skip_logging=True)

    def and_then(self, f: Callable[[T], Option[U]]) -> Option[U]:
        return Nothing(self._reason, _skip_logging=True)

    def or_else(self, f: Callable[[], Option[T]]) -> Option[T]:
        try:
            return f()
        except Exception as e:
            return Nothing.from_exception(e)

    def filter(self, predicate: Callable[[T], bool]) -> Option[T]:
        return Nothing(self._reason, _skip_logging=True)

    def __repr__(self) -> str:
        return f"Nothing({self._reason!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Nothing) and self._reason == other._reason

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Some):
            return True  # Nothing is always less than Some
        elif isinstance(other, Nothing):
            return False  # Nothing values are equal in ordering
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Nothing):
            return True  # Nothing values are equal in ordering
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Some | Nothing):
            return False  # Nothing is never greater than anything
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Nothing):
            return True  # Nothing values are equal in ordering
        return self.__eq__(other) or self.__gt__(other)


# Factory functions for creating Options
def from_nullable[T](value: T | None) -> Option[T]:
    """Convert a nullable value to an Option.

    This function converts a potentially None value into an Option,
    automatically logging if the value is unexpectedly None.

    Args:
        value: An optional value that might be None.

    Returns:
        Some(value) if value is not None, Nothing if value is None.

    Examples:
        With a present value:
        >>> option = from_nullable("hello")
        >>> option.unwrap()
        'hello'

        With None:
        >>> option = from_nullable(None)
        >>> option.unwrap_or("default")
        'default'

        Common usage with dict.get():
        >>> config = {"database_url": "postgres://localhost/db"}
        >>> db_url = from_nullable(config.get("database_url")).unwrap_or("sqlite:///default.db")
        >>> db_url
        'postgres://localhost/db'
    """
    if value is not None:
        return Some(value)
    else:
        return Nothing.from_none()


def from_callable[T](f: Callable[[], T | None]) -> Option[T]:
    """Execute a callable and return Some(result) or Nothing.

    This function safely executes a callable that might return None or raise
    an exception, converting both cases to appropriate Option values with
    automatic logging.

    Args:
        f: A callable that returns an optional value of type T.

    Returns:
        Some(result) if the callable succeeds and returns non-None,
        Nothing if it returns None or raises an exception.

    Examples:
        Successful execution:
        >>> option = from_callable(lambda: "result")
        >>> option.unwrap()
        'result'

        Callable returns None:
        >>> option = from_callable(lambda: None)
        >>> option.unwrap_or("default")
        'default'

        Callable raises exception:
        >>> option = from_callable(lambda: 1 / 0)
        >>> option.is_nothing()
        True

        With file operations:
        >>> import os
        >>> option = from_callable(lambda: os.environ.get("NONEXISTENT_VAR"))
        >>> option.unwrap_or("default_value")
        'default_value'
    """
    try:
        result = f()
        if result is not None:
            return Some(result)
        else:
            return Nothing.from_none("Callable returned None")
    except Exception as e:
        return Nothing.from_exception(e)


def from_predicate(
    value: T, predicate: Callable[[T], bool], *, error_message: str | None = None
) -> Option[T]:
    """Create an Option based on whether a value satisfies a predicate.

    This function tests a value against a predicate function and returns
    Some(value) if the predicate passes, or Nothing if it fails or raises
    an exception.

    Args:
        value: The value to test.
        predicate: Function to test the value against.
        error_message: Custom error message for predicate failure. If None,
                      a default message will be generated.

    Returns:
        Some(value) if predicate(value) is True, Nothing otherwise.

    Examples:
        Predicate passes:
        >>> option = from_predicate(42, lambda x: x > 30)
        >>> option.unwrap()
        42

        Predicate fails:
        >>> option = from_predicate(5, lambda x: x > 30)
        >>> option.unwrap_or(0)
        0

        With custom error message:
        >>> option = from_predicate(5, lambda x: x > 30, error_message="Number too small")
        >>> option.is_nothing()
        True

        With string validation:
        >>> option = from_predicate("hello@example.com", lambda s: "@" in s)
        >>> option.map(str.upper).unwrap_or("INVALID")
        'HELLO@EXAMPLE.COM'

        Predicate raises exception:
        >>> option = from_predicate("text", lambda s: int(s) > 0)
        >>> option.is_nothing()
        True
    """
    try:
        if predicate(value):
            return Some(value)
        else:
            message = error_message or f"Value {value} failed predicate"
            return Nothing.from_filter(message)
    except Exception as e:
        return Nothing.from_exception(e)


def predicate_filter[T](
    predicate: Callable[[T], bool], *, error_message: str | None = None
) -> Callable[[T], Option[T]]:
    """Create a reusable predicate filter function.

    This function returns a curried version of from_predicate, allowing you to
    create reusable validation functions.

    Args:
        predicate: Function to test values against.
        error_message: Custom error message for predicate failure.

    Returns:
        A function that takes a value and returns an Option.

    Examples:
        Create reusable validators:
        >>> is_positive = predicate_filter(lambda x: x > 0, error_message="Must be positive")
        >>> is_positive(42).unwrap()
        42
        >>> is_positive(-5).is_nothing()
        True

        Use with method chaining:
        >>> email_validator = predicate_filter(lambda s: "@" in s, error_message="Invalid email")
        >>> Some("user@example.com").and_then(lambda email: email_validator(email)).is_some()
        True
    """

    def filter_func(value: T) -> Option[T]:
        return from_predicate(value, predicate, error_message=error_message)

    return filter_func
