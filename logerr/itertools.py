"""
Collection-level operations for Option/Result: sequence, traverse,
partition, and values - short-circuiting folds of a *collection* of
Options/Results into one, in the Haskell/Rust `traverse`/`collect` sense.

Everything else in the standard itertools toolkit (chain, filterfalse,
takewhile, ...) already works on Option/Result directly since they're
iterable (see logerr.functools) - this module only adds what plain
itertools has no equivalent for: folding many Options/Results into one
with short-circuit-on-first-failure semantics.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .option import Nothing, Option, Some
from .result import Err, Ok, Result


def sequence_option[T](items: Iterable[Option[T]]) -> Option[list[T]]:
    """Fold an iterable of Options into one Option of a list.

    Short-circuits on the first Nothing.

    Args:
        items: The Options to sequence.

    Returns:
        Some(values) if every item is Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> sequence_option([Some(1), Some(2), Some(3)])
        Some([1, 2, 3])
        >>> sequence_option([Some(1), Nothing.empty(), Some(3)])  # doctest: +ELLIPSIS
        Nothing(...)
        >>> sequence_option([])
        Some([])
    """
    values: list[T] = []
    for item in items:
        if item.is_nothing():
            return Nothing.empty()
        values.append(item.unwrap())
    return Some(values)


def sequence_result[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]:
    """Fold an iterable of Results into one Result of a list.

    Short-circuits on the first Err.

    Args:
        items: The Results to sequence.

    Returns:
        Ok(values) if every item is Ok, otherwise the first Err encountered.

    Examples:
        >>> from logerr import Ok, Err
        >>> sequence_result([Ok(1), Ok(2), Ok(3)])
        Ok([1, 2, 3])
        >>> sequence_result([Ok(1), Err("boom"), Ok(3)])  # doctest: +ELLIPSIS
        Err(...)
        >>> sequence_result([])
        Ok([])
    """
    values: list[T] = []
    for item in items:
        if item.is_err():
            return Err(item.unwrap_err(), _skip_logging=True)
        values.append(item.unwrap())
    return Ok(values)


def traverse_option[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]:
    """Map `func` over `items` and sequence the results.

    Short-circuits: `func` is never called on items after the first one
    that returns Nothing.

    Args:
        items: The values to map over.
        func: A function from T to Option[U].

    Returns:
        Some(values) if every call returns Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some
        >>> traverse_option([1, 2, 3], lambda x: Some(x * 2))
        Some([2, 4, 6])
    """
    return sequence_option(func(item) for item in items)


def traverse_result[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]:
    """Map `func` over `items` and sequence the results.

    Short-circuits: `func` is never called on items after the first one
    that returns Err.

    Args:
        items: The values to map over.
        func: A function from T to Result[U, E].

    Returns:
        Ok(values) if every call returns Ok, otherwise the first Err
        encountered.

    Examples:
        >>> from logerr import Ok
        >>> traverse_result([1, 2, 3], lambda x: Ok(x * 2))
        Ok([2, 4, 6])
    """
    return sequence_result(func(item) for item in items)
