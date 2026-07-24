"""Type stubs for logerr.functools module."""

from __future__ import annotations

from .option import Option
from .result import Result

def zip_option[T, U](a: Option[T], b: Option[U]) -> Option[tuple[T, U]]:
    """Combine two Options into an Option of a tuple."""
    ...

def zip_result[T, U, E](a: Result[T, E], b: Result[U, E]) -> Result[tuple[T, U], E]:
    """Combine two Results into a Result of a tuple."""
    ...

def flatten_option[T](nested: Option[Option[T]]) -> Option[T]:
    """Flatten a nested Option by one level."""
    ...

def flatten_result[T, E](nested: Result[Result[T, E], E]) -> Result[T, E]:
    """Flatten a nested Result by one level."""
    ...

def and_option[T, U](opt: Option[T], other: Option[U]) -> Option[U]:
    """Return other if opt is Some, otherwise Nothing."""
    ...

def and_result[T, U, E](res: Result[T, E], other: Result[U, E]) -> Result[U, E]:
    """Return other if res is Ok, otherwise the original Err."""
    ...

def or_option[T](opt: Option[T], other: Option[T]) -> Option[T]:
    """Return opt if Some, otherwise other."""
    ...

def or_result[T, E, F](res: Result[T, E], other: Result[T, F]) -> Result[T, F]:
    """Return res if Ok, otherwise other."""
    ...

def ok[T, E](result: Result[T, E]) -> Option[T]:
    """Convert a Result into an Option, discarding any error."""
    ...

def err[T, E](result: Result[T, E]) -> Option[E]:
    """Convert a Result into an Option of its error."""
    ...
