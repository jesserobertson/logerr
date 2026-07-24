"""
Functional combinators for Option/Result, mirroring Rust's Option/Result
API surface (zip, flatten, and, or, ok, err).

These are pure value combinators - none of them invoke a user-supplied
callable, so there is no exception to catch: a Nothing/Err input just
propagates, matching the corresponding value's existing state. All
functions here use only the public API of Option/Result
(is_some/is_nothing/is_ok/is_err/unwrap/unwrap_err) - never private
_value/_error/_reason attributes.

Note there's no bespoke "polymorphic zip" here: Some/Nothing/Ok/Err are
iterable, yielding their value 0 or 1 times, so Python's own
builtins.zip() already works correctly on them directly - no wrapper
needed, and no risk of a logerr zip() behaving differently from the
real one. zip_option/zip_result below are a deliberately distinct,
explicitly-named operation: combining two Options/Results into one
Option/Result of a tuple.
"""

from __future__ import annotations

from .option import Nothing, Option, Some
from .result import Err, Ok, Result


def zip_option[T, U](a: Option[T], b: Option[U]) -> Option[tuple[T, U]]:
    """Combine two Options into an Option of a tuple.

    Args:
        a: The first Option.
        b: The second Option.

    Returns:
        Some((a_value, b_value)) if both are Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> zip_option(Some(1), Some("a"))
        Some((1, 'a'))
        >>> zip_option(Nothing.empty(), Some("a"))
        Nothing('Empty option')
    """
    if a.is_some() and b.is_some():
        return Some((a.unwrap(), b.unwrap()))
    return Nothing.empty()


def zip_result[T, U, E](a: Result[T, E], b: Result[U, E]) -> Result[tuple[T, U], E]:
    """Combine two Results into a Result of a tuple.

    Args:
        a: The first Result.
        b: The second Result.

    Returns:
        Ok((a_value, b_value)) if both are Ok, otherwise the first Err
        encountered (checking a before b).

    Examples:
        >>> from logerr import Ok, Err
        >>> zip_result(Ok(1), Ok("a"))
        Ok((1, 'a'))
        >>> zip_result(Err("boom"), Ok("a"))  # doctest: +ELLIPSIS
        Err(...)
    """
    if a.is_err():
        return Err(a.unwrap_err(), _skip_logging=True)
    if b.is_err():
        return Err(b.unwrap_err(), _skip_logging=True)
    return Ok((a.unwrap(), b.unwrap()))


def flatten_option[T](nested: Option[Option[T]]) -> Option[T]:
    """Flatten a nested Option by one level.

    Args:
        nested: An Option containing another Option.

    Returns:
        The inner Option if the outer is Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> flatten_option(Some(Some(42)))
        Some(42)
        >>> flatten_option(Nothing.empty())
        Nothing('Empty option')
    """
    if nested.is_some():
        return nested.unwrap()
    return Nothing.empty()


def flatten_result[T, E](nested: Result[Result[T, E], E]) -> Result[T, E]:
    """Flatten a nested Result by one level.

    Args:
        nested: A Result containing another Result, sharing the same
            error type.

    Returns:
        The inner Result if the outer is Ok, otherwise the outer Err.

    Examples:
        >>> from logerr import Ok, Err
        >>> flatten_result(Ok(Ok(42)))
        Ok(42)
        >>> flatten_result(Err("outer boom"))  # doctest: +ELLIPSIS
        Err(...)
    """
    if nested.is_err():
        return Err(nested.unwrap_err(), _skip_logging=True)
    return nested.unwrap()


def and_option[T, U](opt: Option[T], other: Option[U]) -> Option[U]:
    """Return `other` if `opt` is Some, otherwise Nothing.

    Args:
        opt: The Option to check.
        other: The Option to return if `opt` is Some.

    Returns:
        `other` if `opt` is Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> and_option(Some(1), Some("a"))
        Some('a')
        >>> and_option(Nothing.empty(), Some("a"))
        Nothing('Empty option')
    """
    if opt.is_some():
        return other
    return Nothing.empty()


def and_result[T, U, E](res: Result[T, E], other: Result[U, E]) -> Result[U, E]:
    """Return `other` if `res` is Ok, otherwise the original Err.

    Args:
        res: The Result to check.
        other: The Result to return if `res` is Ok.

    Returns:
        `other` if `res` is Ok, otherwise `res`'s error re-wrapped.

    Examples:
        >>> from logerr import Ok, Err
        >>> and_result(Ok(1), Ok("a"))
        Ok('a')
        >>> and_result(Err("boom"), Ok("a"))  # doctest: +ELLIPSIS
        Err(...)
    """
    if res.is_err():
        return Err(res.unwrap_err(), _skip_logging=True)
    return other


def or_option[T](opt: Option[T], other: Option[T]) -> Option[T]:
    """Return `opt` if it's Some, otherwise `other`.

    Args:
        opt: The Option to check.
        other: The fallback Option if `opt` is Nothing.

    Returns:
        `opt` if Some, otherwise `other`.

    Examples:
        >>> from logerr import Some, Nothing
        >>> or_option(Some(1), Some(2))
        Some(1)
        >>> or_option(Nothing.empty(), Some(2))
        Some(2)
    """
    if opt.is_some():
        return opt
    return other


def or_result[T, E, F](res: Result[T, E], other: Result[T, F]) -> Result[T, F]:
    """Return `res` if it's Ok, otherwise `other`.

    Args:
        res: The Result to check.
        other: The fallback Result if `res` is Err. May have a different
            error type than `res`.

    Returns:
        `res`'s value re-wrapped if Ok, otherwise `other`.

    Examples:
        >>> from logerr import Ok, Err
        >>> or_result(Ok(1), Err("fallback"))
        Ok(1)
        >>> or_result(Err("primary"), Ok(2))
        Ok(2)
    """
    if res.is_ok():
        return Ok(res.unwrap())
    return other
