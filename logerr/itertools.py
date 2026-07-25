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

import itertools
from collections.abc import Callable, Iterable, Iterator
from typing import Any, overload

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


def partition_option[T](items: Iterable[Option[T]]) -> tuple[list[T], int]:
    """Split an iterable of Options into present values and a Nothing count.

    Unlike sequence_option, this does not short-circuit - every item is
    visited.

    Args:
        items: The Options to partition.

    Returns:
        A tuple of (values, nothing_count).

    Examples:
        >>> from logerr import Some, Nothing
        >>> partition_option([Some(1), Nothing.empty(), Some(3)])
        ([1, 3], 1)
    """
    values: list[T] = []
    nothing_count = 0
    for item in items:
        if item.is_some():
            values.append(item.unwrap())
        else:
            nothing_count += 1
    return values, nothing_count


def partition_result[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]:
    """Split an iterable of Results into Ok values and Err values.

    Unlike sequence_result, this does not short-circuit - every item is
    visited.

    Args:
        items: The Results to partition.

    Returns:
        A tuple of (oks, errs).

    Examples:
        >>> from logerr import Ok, Err
        >>> partition_result([Ok(1), Err("boom"), Ok(3)])
        ([1, 3], ['boom'])
    """
    oks: list[T] = []
    errs: list[E] = []
    for item in items:
        if item.is_ok():
            oks.append(item.unwrap())
        else:
            errs.append(item.unwrap_err())
    return oks, errs


def fold_option[T, U](
    items: Iterable[U], initial: T, func: Callable[[T, U], Option[T]]
) -> Option[T]:
    """Thread an accumulator through items, short-circuiting on Nothing.

    Mirrors Rust's Iterator::try_fold. Unlike sequence_option/traverse_option
    (which treat items independently), each call to func receives the
    accumulator produced by the previous call - this is explicitly
    sequential, not parallelizable.

    Args:
        items: The values to fold over.
        initial: The starting accumulator value.
        func: Called as func(accumulator, item) -> Option[new_accumulator].

    Returns:
        Some(final_accumulator) if every call returns Some, otherwise
        Nothing from the first call that does.

    Examples:
        >>> from logerr import Some
        >>> fold_option([1, 2, 3], 0, lambda acc, x: Some(acc + x))
        Some(6)
        >>> from logerr import Nothing
        >>> fold_option([1, 2, 3], 0, lambda acc, x: Nothing.empty() if x == 2 else Some(acc + x))  # doctest: +ELLIPSIS
        Nothing(...)
    """
    acc = initial
    for item in items:
        result = func(acc, item)
        if result.is_nothing():
            return Nothing.empty()
        acc = result.unwrap()
    return Some(acc)


def fold_result[T, U, E](
    items: Iterable[U], initial: T, func: Callable[[T, U], Result[T, E]]
) -> Result[T, E]:
    """Thread an accumulator through items, short-circuiting on Err.

    Mirrors Rust's Iterator::try_fold. Unlike sequence_result/traverse_result
    (which treat items independently), each call to func receives the
    accumulator produced by the previous call - this is explicitly
    sequential, not parallelizable.

    Args:
        items: The values to fold over.
        initial: The starting accumulator value.
        func: Called as func(accumulator, item) -> Result[new_accumulator, E].

    Returns:
        Ok(final_accumulator) if every call returns Ok, otherwise the
        first Err encountered.

    Examples:
        >>> from logerr import Ok
        >>> fold_result([1, 2, 3], 0, lambda acc, x: Ok(acc + x))
        Ok(6)
        >>> from logerr import Err
        >>> fold_result([1, 2, 3], 0, lambda acc, x: Err("boom") if x == 2 else Ok(acc + x))  # doctest: +ELLIPSIS
        Err(...)
    """
    acc = initial
    for item in items:
        result = func(acc, item)
        if result.is_err():
            return Err(result.unwrap_err(), _skip_logging=True)
        acc = result.unwrap()
    return Ok(acc)


@overload
def values[T](items: Iterable[Option[T]]) -> Iterator[T]: ...
@overload
def values[T](items: Iterable[Result[T, Any]]) -> Iterator[T]: ...
def values(items: Iterable[Any]) -> Iterator[Any]:
    """Yield the present/Ok values from a collection of Options/Results.

    Lazy - drops Nothing/Err entries without raising or collecting error
    information. Use partition_option/partition_result if you need the
    failures too.

    Args:
        items: The Options or Results to extract values from.

    Returns:
        An iterator over the contained values.

    Examples:
        >>> from logerr import Some, Nothing
        >>> list(values([Some(1), Nothing.empty(), Some(3)]))
        [1, 3]
        >>> from logerr import Ok, Err
        >>> list(values([Ok(1), Err("boom"), Ok(3)]))
        [1, 3]
    """
    return itertools.chain.from_iterable(items)


@overload
def sequence[T](items: Iterable[Option[T]]) -> Option[list[T]]: ...
@overload
def sequence[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]: ...
def sequence(items: Iterable[Any]) -> Any:
    """Fold a collection of Options or Results into one.

    Dispatches on the first element's runtime type. For the unambiguous,
    always-available alternative, use sequence_option/sequence_result
    directly.

    Args:
        items: An iterable of Options or Results.

    Returns:
        Some(values) or Ok(values) if all items succeed, otherwise
        Nothing or the first Err encountered, depending on whether items
        contains Options or Results.

    Raises:
        ValueError: If `items` is empty.
        TypeError: If the first element is neither an Option nor a Result.

    Examples:
        >>> from logerr import Some
        >>> sequence([Some(1), Some(2)])
        Some([1, 2])
    """
    it = iter(items)
    try:
        first = next(it)
    except StopIteration:
        raise ValueError(
            "sequence() cannot infer Option vs Result from an empty "
            "iterable; use sequence_option([]) or sequence_result([]) "
            "directly"
        ) from None
    rest = itertools.chain([first], it)
    if isinstance(first, Some | Nothing):
        return sequence_option(rest)
    if isinstance(first, Ok | Err):
        return sequence_result(rest)
    raise TypeError(f"sequence() expects Option or Result items, got {type(first)!r}")


@overload
def traverse[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]: ...
@overload
def traverse[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]: ...
def traverse(items: Iterable[Any], func: Callable[[Any], Any]) -> Any:
    """Map `func` over `items` and sequence the results.

    Dispatches on the type of `func`'s first return value. `func` is
    called exactly once per item regardless of dispatch (the first call's
    result is reused, never recomputed).

    Args:
        items: The values to map over.
        func: A function that returns Option or Result.

    Returns:
        Some(values) or Ok(values) if all function calls succeed,
        otherwise Nothing or the first Err encountered, depending on
        whether func returns Options or Results.

    Raises:
        ValueError: If `items` is empty.
        TypeError: If `func`'s return value is neither an Option nor a
            Result.

    Examples:
        >>> from logerr import Some
        >>> traverse([1, 2, 3], lambda x: Some(x * 2))
        Some([2, 4, 6])
    """
    it = iter(items)
    try:
        first_item = next(it)
    except StopIteration:
        raise ValueError(
            "traverse() cannot infer Option vs Result from an empty "
            "iterable; use traverse_option([], func) or "
            "traverse_result([], func) directly"
        ) from None
    first_result = func(first_item)
    rest = (func(item) for item in it)
    if isinstance(first_result, Some | Nothing):
        return sequence_option(itertools.chain([first_result], rest))
    if isinstance(first_result, Ok | Err):
        return sequence_result(itertools.chain([first_result], rest))
    raise TypeError(
        "traverse() expects func to return Option or Result, "
        f"got {type(first_result)!r}"
    )


@overload
def partition[T](items: Iterable[Option[T]]) -> tuple[list[T], int]: ...
@overload
def partition[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]: ...
def partition(items: Iterable[Any]) -> tuple[list[Any], Any]:
    """Partition a collection of Options or Results.

    Dispatches on the first element's runtime type.

    Args:
        items: An iterable of Options or Results.

    Returns:
        If items contains Options: (values, nothing_count).
        If items contains Results: (oks, errs).

    Raises:
        ValueError: If `items` is empty.
        TypeError: If the first element is neither an Option nor a Result.

    Examples:
        >>> from logerr import Some, Nothing
        >>> partition([Some(1), Nothing.empty(), Some(3)])
        ([1, 3], 1)
    """
    materialized = list(items)
    if not materialized:
        raise ValueError(
            "partition() cannot infer Option vs Result from an empty "
            "iterable; use partition_option([]) or partition_result([]) "
            "directly"
        )
    first = materialized[0]
    if isinstance(first, Some | Nothing):
        return partition_option(materialized)
    if isinstance(first, Ok | Err):
        return partition_result(materialized)
    raise TypeError(f"partition() expects Option or Result items, got {type(first)!r}")


@overload
def fold[T, U](
    items: Iterable[U], initial: T, func: Callable[[T, U], Option[T]]
) -> Option[T]: ...
@overload
def fold[T, U, E](
    items: Iterable[U], initial: T, func: Callable[[T, U], Result[T, E]]
) -> Result[T, E]: ...
def fold(items: Iterable[Any], initial: Any, func: Callable[[Any, Any], Any]) -> Any:
    """Thread an accumulator through items via func, dispatching on func's return type.

    Dispatches on the type of func's first return value (func is called
    once on the first item to determine Option vs Result, then the
    remaining items are processed by delegating to fold_option/fold_result
    - func is never called twice on the first item).

    Args:
        items: The values to fold over.
        initial: The starting accumulator value.
        func: Called as func(accumulator, item) -> Option[T] or Result[T, E].

    Returns:
        The final accumulator wrapped in Some/Ok, or the first
        Nothing/Err encountered.

    Raises:
        ValueError: If `items` is empty.
        TypeError: If `func`'s return value is neither an Option nor a
            Result.

    Examples:
        >>> from logerr import Some
        >>> fold([1, 2, 3], 0, lambda acc, x: Some(acc + x))
        Some(6)
    """
    it = iter(items)
    try:
        first_item = next(it)
    except StopIteration:
        raise ValueError(
            "fold() cannot infer Option vs Result from an empty "
            "iterable; use fold_option([], initial, func) or "
            "fold_result([], initial, func) directly"
        ) from None
    first_result = func(initial, first_item)
    if isinstance(first_result, Some | Nothing):
        if first_result.is_nothing():
            return Nothing.empty()
        return fold_option(it, first_result.unwrap(), func)
    if isinstance(first_result, Ok | Err):
        if first_result.is_err():
            return Err(first_result.unwrap_err(), _skip_logging=True)
        return fold_result(it, first_result.unwrap(), func)
    raise TypeError(
        f"fold() expects func to return Option or Result, got {type(first_result)!r}"
    )
