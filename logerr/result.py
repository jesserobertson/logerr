"""
Result type implementation with automatic logging integration.

Provides Rust-like Result<T, E> types with automatic logging from error cases
through loguru, configurable via confection.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from .option import Option

from loguru import logger

from .config import get_log_level, should_log

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


class Result[T, E](ABC):
    """A type that represents either success (Ok) or failure (Err).

    Result<T, E> is similar to Rust's Result type, providing a way to handle
    operations that might fail without using exceptions. When an Err is created,
    it's automatically logged using loguru with configurable log levels and formats.

    Type Parameters:
        T: The type from the success value
        E: The type from the error value

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
    def unwrap_err(self) -> E:
        """Extract the error value, raising an exception if this is an Ok.

        Returns:
            The contained Err value.

        Raises:
            RuntimeError: If this Result is an Ok.

        Examples:
            >>> Err("failed").unwrap_err()
            'failed'
            >>> Ok(42).unwrap_err()  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            RuntimeError: Called unwrap_err on Ok: 42
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
    def map[U](self, f: Callable[[T], U]) -> Result[U, E]:
        """Transform the success value if present.

        Args:
            f: Function to transform the Ok value.

        Returns:
            Ok(f(value)) if this is Ok, otherwise the original Err.

        Note:
            Exceptions raised by f are not caught here - they propagate to
            the caller, matching Rust's Result::map. Use execute()/of() at
            the point where you construct a Result if you want exceptions
            converted to Err automatically.

        Examples:
            >>> Ok(5).map(lambda x: x * 2)
            Ok(10)
            >>> Err("failed").map(lambda x: x * 2)
            Err('failed')
        """
        pass

    @abstractmethod
    def map_err[U](self, f: Callable[[E], U]) -> Result[T, U]:
        """Transform the error value if present.

        Args:
            f: Function to transform the Err value.

        Returns:
            Err(f(error)) if this is Err, otherwise the original Ok.

        Note:
            Exceptions raised by f are not caught here - they propagate to
            the caller.

        Examples:
            >>> Ok(42).map_err(str)
            Ok(42)
            >>> Err(404).map_err(str)
            Err('404')
        """
        pass

    @abstractmethod
    def then[U](self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain Result-returning operations (also known as flatmap).

        Args:
            f: Function that takes the Ok value and returns a new Result.

        Returns:
            f(value) if this is Ok, otherwise the original Err.

        Note:
            Exceptions raised by f are not caught here - they propagate to
            the caller, matching Rust's Result::and_then.

        Examples:
            >>> def divide(x: int) -> Result[float, str]:
            ...     if x == 0:
            ...         return Err("division by zero")
            ...     return Ok(10.0 / x)
            >>> Ok(2).then(divide)
            Ok(5.0)
            >>> Ok(0).then(divide)
            Err('division by zero')
        """
        pass

    @abstractmethod
    def or_else[U](self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        """Chain Result-returning operations on the error case.

        Args:
            f: Function that takes the Err value and returns a new Result.

        Returns:
            The original Ok if this is Ok, otherwise f(error).

        Note:
            Exceptions raised by f are not caught here - they propagate to
            the caller, matching Rust's Result::or_else.

        Examples:
            >>> def retry(error: str) -> Result[int, str]:
            ...     return Ok(99) if "retry" in error else Err("permanent failure")
            >>> Ok(42).or_else(retry)
            Ok(42)
            >>> Err("retry needed").or_else(retry)
            Ok(99)

            For simple defaults, consider using unwrap_or():
            >>> Err("failed").unwrap_or(42)
            42
        """
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Iterate over the Ok value, 0 or 1 times.

        Matches Rust's Result::iter() - the Err value is never yielded,
        only the Ok value if present. Lets Result compose with the
        standard iterator toolkit (zip, itertools, etc.) directly.

        Returns:
            An iterator yielding the value once if Ok, or nothing if Err.

        Examples:
            >>> list(Ok(42))
            [42]
            >>> list(Err("boom"))
            []
        """
        pass

    @abstractmethod
    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]:
        """Combine this Result with another into a Result of a tuple.

        Args:
            other: The Result to combine with.

        Returns:
            Ok((value, other_value)) if both are Ok, otherwise the first
            Err encountered (checking self before other).

        Examples:
            >>> Ok(1).zip(Ok("a"))
            Ok((1, 'a'))
            >>> Ok(1).zip(Err("boom"))  # doctest: +ELLIPSIS
            Err(...)
        """
        pass

    @abstractmethod
    def flatten(self: Result[Result[T, E], E]) -> Result[T, E]:
        """Flatten a nested Result by one level.

        Returns:
            The inner Result if this is Ok, otherwise this Err.

        Examples:
            >>> Ok(Ok(42)).flatten()
            Ok(42)
        """
        pass

    @abstractmethod
    def and_[U](self, other: Result[U, E]) -> Result[U, E]:
        """Return `other` if this is Ok, otherwise this Err.

        Args:
            other: The Result to return if this is Ok.

        Returns:
            `other` if this is Ok, otherwise this Err re-wrapped.

        Examples:
            >>> Ok(1).and_(Ok("a"))
            Ok('a')
            >>> Err("boom").and_(Ok("a"))  # doctest: +ELLIPSIS
            Err(...)
        """
        pass

    @abstractmethod
    def or_[F](self, other: Result[T, F]) -> Result[T, F]:
        """Return this Result if Ok, otherwise `other`.

        Args:
            other: The fallback Result if this is Err. May have a
                different error type than this Result.

        Returns:
            This Result's value re-wrapped if Ok, otherwise `other`.

        Examples:
            >>> Ok(1).or_(Err("fallback"))
            Ok(1)
            >>> Err("primary").or_(Ok(2))
            Ok(2)
        """
        pass

    @abstractmethod
    def ok(self) -> Option[T]:
        """Convert this Result into an Option, discarding any error.

        Returns:
            Some(value) if Ok, otherwise Nothing.

        Examples:
            >>> Ok(42).ok()
            Some(42)
            >>> Err("boom").ok()  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass

    @abstractmethod
    def err(self) -> Option[E]:
        """Convert this Result into an Option of its error.

        Returns:
            Some(error) if Err, otherwise Nothing.

        Examples:
            >>> Err("boom").err()
            Some('boom')
            >>> Ok(42).err()  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """Hash this Result, consistent with __eq__.

        Returns:
            A hash derived from the concrete class and its contained value,
            so that `a == b` implies `hash(a) == hash(b)`.

        Examples:
            >>> hash(Ok(1)) == hash(Ok(1))
            True
        """
        pass

    @abstractmethod
    def __bool__(self) -> bool:
        """Return whether this Result is truthy.

        Returns:
            True if this is Ok, False if Err.

        Examples:
            >>> bool(Ok(42))
            True
            >>> bool(Err("boom"))
            False
        """
        pass

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of contained success values (0 or 1).

        Mirrors __iter__'s "0 or 1 elements" framing.

        Returns:
            1 if this is Ok, 0 if Err.

        Examples:
            >>> len(Ok(42))
            1
            >>> len(Err("boom"))
            0
        """
        pass

    @abstractmethod
    def __contains__(self, item: object) -> bool:
        """Check whether `item` equals the contained Ok value.

        Never checks against the error value - membership testing means
        "does this contain the success value x", not "is this the error".

        Args:
            item: The value to test for membership.

        Returns:
            True if this is Ok and its value equals `item`, otherwise False.

        Examples:
            >>> 42 in Ok(42)
            True
            >>> 42 in Err("boom")
            False
        """
        pass

    @abstractmethod
    def __and__[U](self, other: Result[U, E]) -> Result[U, E]:
        """Thin delegate to and_() - return `other` if this is Ok, otherwise this Err.

        Args:
            other: The Result to return if this is Ok.

        Returns:
            `other` if this is Ok, otherwise this Err re-wrapped.

        Examples:
            >>> Ok(1) & Ok("a")
            Ok('a')
            >>> Err("boom") & Ok("a")  # doctest: +ELLIPSIS
            Err(...)
        """
        pass

    @abstractmethod
    def __or__[F](self, other: Result[T, F]) -> Result[T, F]:
        """Thin delegate to or_() - return this Result if Ok, otherwise `other`.

        Args:
            other: The fallback Result if this is Err. May have a
                different error type than this Result.

        Returns:
            This Result's value re-wrapped if Ok, otherwise `other`.

        Examples:
            >>> Ok(1) | Err("fallback")
            Ok(1)
            >>> Err("primary") | Ok(2)
            Ok(2)
        """
        pass

    @classmethod
    def of(cls, f: Callable[[], T]) -> Result[T, Exception]:
        """Create a Result from a callable that might raise an exception."""
        try:
            return Ok(f())
        except Exception as e:
            return Err.from_exception(e)

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

    @classmethod
    def sequence(cls, items: Iterable[Result[T, E]]) -> Result[list[T], E]:
        """Fold an iterable of Results into one Result of a list.

        Args:
            items: The Results to sequence.

        Returns:
            Ok(values) if every item is Ok, otherwise the first Err encountered.

        Examples:
            >>> Result.sequence([Ok(1), Ok(2)])
            Ok([1, 2])
        """
        from .itertools import sequence_result

        return sequence_result(items)

    @classmethod
    def traverse[U](
        cls, items: Iterable[U], func: Callable[[U], Result[T, E]]
    ) -> Result[list[T], E]:
        """Map `func` over `items` and sequence the results.

        Args:
            items: The values to map over.
            func: A function that returns a Result.

        Returns:
            Ok(values) if every call returns Ok, otherwise the first Err encountered.

        Examples:
            >>> Result.traverse([1, 2, 3], lambda x: Ok(x * 2))
            Ok([2, 4, 6])
        """
        from .itertools import traverse_result

        return traverse_result(items, func)

    @classmethod
    def fold[U](
        cls, items: Iterable[U], initial: T, func: Callable[[T, U], Result[T, E]]
    ) -> Result[T, E]:
        """Thread an accumulator through items, short-circuiting on Err.

        Args:
            items: The values to fold over.
            initial: The starting accumulator value.
            func: Called as func(accumulator, item) -> Result[new_accumulator, E].

        Returns:
            Ok(final_accumulator) if every call returns Ok, otherwise the
            first Err encountered.

        Examples:
            >>> Result.fold([1, 2, 3], 0, lambda acc, x: Ok(acc + x))
            Ok(6)
        """
        from .itertools import fold_result

        return fold_result(items, initial, func)


class Ok[T, E](Result[T, E]):
    """Represents a successful result containing a value.

    Ok is the success variant from Result<T, E>. It wraps a value from type T
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

    __match_args__ = ("_value",)

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

    def map[U](self, f: Callable[[T], U]) -> Result[U, E]:
        return Ok(f(self._value))

    def map_err[U](self, f: Callable[[E], U]) -> Result[T, U]:
        return Ok(self._value)

    def then[U](self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return f(self._value)

    def or_else[U](self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        return Ok(self._value)

    def __iter__(self) -> Iterator[T]:
        yield self._value

    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]:
        from .functools import zip_result

        return zip_result(self, other)

    def flatten(self: Ok[Result[T, E], E]) -> Result[T, E]:
        from .functools import flatten_result

        return flatten_result(self)

    def and_[U](self, other: Result[U, E]) -> Result[U, E]:
        from .functools import and_result

        return and_result(self, other)

    def or_[F](self, other: Result[T, F]) -> Result[T, F]:
        from .functools import or_result

        return or_result(self, other)

    def ok(self) -> Option[T]:
        from .functools import ok as ok_fn

        return ok_fn(self)

    def err(self) -> Option[E]:
        from .functools import err as err_fn

        return err_fn(self)

    def __hash__(self) -> int:
        return hash((Ok, self._value))

    def __bool__(self) -> bool:
        return True

    def __len__(self) -> int:
        return 1

    def __contains__(self, item: object) -> bool:
        return bool(self._value == item)

    def __and__[U](self, other: Result[U, E]) -> Result[U, E]:
        return self.and_(other)

    def __or__[F](self, other: Result[T, F]) -> Result[T, F]:
        return self.or_(other)

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ok) and self._value == other._value

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        match other:
            case Ok(other_value):
                try:
                    result = self._value < other_value
                    return bool(result)
                except TypeError:
                    return NotImplemented
            case Err():
                return False  # Ok is always greater than Err
            case _:
                return NotImplemented

    def __le__(self, other: object) -> bool:
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other: object) -> bool:
        match other:
            case Ok(other_value):
                try:
                    result = self._value > other_value
                    return bool(result)
                except TypeError:
                    return NotImplemented
            case Err():
                return True  # Ok is always greater than Err
            case _:
                return NotImplemented

    def __ge__(self, other: object) -> bool:
        return self.__eq__(other) or self.__gt__(other)


class Err[T, E](Result[T, E]):
    """Represents a failed result containing an error.

    Err is the failure variant from Result<T, E>. It wraps an error value from type E
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

    __match_args__ = ("_error",)

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
        # Check if logging is enabled globally
        if not should_log():
            return

        # Get the calling frame to capture basic context
        frame = inspect.currentframe()
        caller_frame = None

        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back

        # Capture basic context
        context: dict[str, Any] = {}
        if caller_frame:
            from pathlib import Path

            context["function"] = caller_frame.f_code.co_name
            context["file"] = Path(caller_frame.f_code.co_filename).name
            context["line"] = caller_frame.f_lineno

        # Get log level
        log_level = get_log_level()

        # Build simple log message
        location = f"{context.get('function', '<?>')}:{context.get('line', '?')}"
        message = f"Result error in {location} - {self._error}"

        # Log at the configured level
        logger.bind(**context).log(log_level, message)

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
        match self._error:
            case Exception() as e:
                raise e
            case _:
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

    def map[U](self, f: Callable[[T], U]) -> Result[U, E]:
        return Err(self._error, _skip_logging=True)

    def map_err[U](self, f: Callable[[E], U]) -> Result[T, U]:
        return Err(f(self._error))

    def then[U](self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return Err(self._error, _skip_logging=True)

    def or_else[U](self, f: Callable[[E], Result[T, U]]) -> Result[T, U]:
        return f(self._error)

    def __iter__(self) -> Iterator[T]:
        return iter(())

    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]:
        from .functools import zip_result

        return zip_result(self, other)

    def flatten(self: Err[Result[T, E], E]) -> Result[T, E]:
        from .functools import flatten_result

        return flatten_result(self)

    def and_[U](self, other: Result[U, E]) -> Result[U, E]:
        from .functools import and_result

        return and_result(self, other)

    def or_[F](self, other: Result[T, F]) -> Result[T, F]:
        from .functools import or_result

        return or_result(self, other)

    def ok(self) -> Option[T]:
        from .functools import ok as ok_fn

        return ok_fn(self)

    def err(self) -> Option[E]:
        from .functools import err as err_fn

        return err_fn(self)

    def __hash__(self) -> int:
        return hash((Err, self._error))

    def __bool__(self) -> bool:
        return False

    def __len__(self) -> int:
        return 0

    def __contains__(self, item: object) -> bool:
        return False

    def __and__[U](self, other: Result[U, E]) -> Result[U, E]:
        return self.and_(other)

    def __or__[F](self, other: Result[T, F]) -> Result[T, F]:
        return self.or_(other)

    def __repr__(self) -> str:
        return f"Err({self._error!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Err) and self._error == other._error

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        match other:
            case Err(other_error):
                try:
                    result = self._error < other_error
                    return bool(result)
                except TypeError:
                    return NotImplemented
            case Ok():
                return True  # Err is always less than Ok
            case _:
                return NotImplemented

    def __le__(self, other: object) -> bool:
        return self.__eq__(other) or self.__lt__(other)

    def __gt__(self, other: object) -> bool:
        match other:
            case Err(other_error):
                try:
                    result = self._error > other_error
                    return bool(result)
                except TypeError:
                    return NotImplemented
            case Ok():
                return False  # Err is never greater than Ok
            case _:
                return NotImplemented

    def __ge__(self, other: object) -> bool:
        return self.__eq__(other) or self.__gt__(other)


# Factory functions for creating Results
def of[T](f: Callable[[], T]) -> Result[T, Exception]:
    """Execute a callable and return Ok(result) or Err(exception).

    This function safely executes a callable that might raise an exception,
    capturing any exceptions and converting them to Err results with automatic logging.

    Args:
        f: A callable that returns a value from type T.

    Returns:
        Ok(result) if the callable succeeds, Err(exception) if it raises.

    Examples:
        Successful execution:
        >>> result = of(lambda: 42)
        >>> result.unwrap()
        42

        Handling exceptions:
        >>> result = of(lambda: 1 / 0)
        >>> result.is_err()
        True
        >>> result.unwrap_or(0)
        0

        With more complex operations:
        >>> import json
        >>> result = of(lambda: json.loads('{"key": "value"}'))
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

    This function returns a curried version from from_predicate, allowing you to
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
        >>> Ok("user@example.com").then(email_validator).is_ok()
        True
    """

    def validator_func(value: T) -> Result[T, E]:
        # Type: ignore because from_predicate might return Exception in error case
        return from_predicate(value, predicate, error)  # type: ignore[return-value]

    return validator_func
