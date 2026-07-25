"""Type stubs for logerr.itertools module."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, overload

from .option import Option
from .result import Result

def sequence_option[T](items: Iterable[Option[T]]) -> Option[list[T]]:
    """Fold an iterable of Options into one Option of a list."""
    ...

def sequence_result[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]:
    """Fold an iterable of Results into one Result of a list."""
    ...

def traverse_option[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]:
    """Map func over items and sequence the results."""
    ...

def traverse_result[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]:
    """Map func over items and sequence the results."""
    ...

def partition_option[T](items: Iterable[Option[T]]) -> tuple[list[T], int]:
    """Split an iterable of Options into present values and a Nothing count."""
    ...

def partition_result[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]:
    """Split an iterable of Results into Ok values and Err values."""
    ...

def fold_option[T, U](
    items: Iterable[U], initial: T, func: Callable[[T, U], Option[T]]
) -> Option[T]:
    """Thread an accumulator through items, short-circuiting on Nothing."""
    ...

def fold_result[T, U, E](
    items: Iterable[U], initial: T, func: Callable[[T, U], Result[T, E]]
) -> Result[T, E]:
    """Thread an accumulator through items, short-circuiting on Err."""
    ...

@overload
def values[T](items: Iterable[Option[T]]) -> Iterator[T]: ...
@overload
def values[T](items: Iterable[Result[T, Any]]) -> Iterator[T]: ...
@overload
def sequence[T](items: Iterable[Option[T]]) -> Option[list[T]]: ...
@overload
def sequence[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]: ...
@overload
def traverse[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]: ...
@overload
def traverse[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]: ...
@overload
def partition[T](items: Iterable[Option[T]]) -> tuple[list[T], int]: ...
@overload
def partition[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]: ...
@overload
def fold[T, U](
    items: Iterable[U], initial: T, func: Callable[[T, U], Option[T]]
) -> Option[T]: ...
@overload
def fold[T, U, E](
    items: Iterable[U], initial: T, func: Callable[[T, U], Result[T, E]]
) -> Result[T, E]: ...
