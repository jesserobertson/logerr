"""
Functional retry patterns for Result types with automatic logging.

This module provides lightweight, functional retry patterns that integrate with
Result types and automatically log retry attempts using loguru.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar, cast

from loguru import logger
from tenacity import (  # type: ignore[import-not-found]
    RetryCallState,
    RetryError,
    Retrying,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

from ..option import Option
from ..result import Err, Ok, Result

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


def _make_retry_wrapper(
    func: Callable[..., Result[T, E]],
    *,
    error_types: tuple[type[Exception], ...] | None,
    stop: Any,
    wait: Any,
    log_attempts: bool,
    retry_if: Callable[[E], bool] | None,
    before_attempt: Callable[[int], None] | None,
    on_retry: Callable[[int, E], None] | None,
) -> Callable[..., Result[T, E]]:
    """Shared implementation behind ``on_err``/``on_err_type``.

    Both decorators retry a ``Result``-returning function by converting a
    retryable ``Err`` into a raised exception tenacity can see, then
    converting back to ``Result`` at the edges. ``error_types`` is the only
    thing that differs between them (``None`` for ``on_err``, the type tuple
    for ``on_err_type``); everything else - the retry loop, the hooks, the
    logging shape - is identical, so it lives here once.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, E]:
        last_result: Result[T, E] | None = None
        attempt_count = 0
        # Reset at the top of every attempt (see below) so a stale value
        # from an earlier attempt's Err can never leak into this attempt's
        # on_retry call.
        attempt_error: E | None = None

        actual_stop = Option.from_nullable(stop).unwrap_or_else(
            lambda: stop_after_attempt(3)
        )
        actual_wait = Option.from_nullable(wait).unwrap_or_else(
            lambda: wait_exponential(multiplier=1, min=4, max=10)
        )

        # Defined unconditionally (not just under `if log_attempts`) so it's
        # always available - including in the RetryError handler below.
        func_name = Option.of(lambda: func.__name__).unwrap_or("callable")

        if log_attempts:
            if error_types is not None:
                logger.debug(
                    f"Starting retry operation for {func_name} "
                    f"(retrying on: {error_types})"
                )
            else:
                logger.debug(f"Starting retry operation for {func_name}")

        def _before_sleep(retry_state: RetryCallState) -> None:
            # Only invoked by tenacity when it has already decided to retry
            # (not on the final, exhausting attempt), which is exactly
            # on_retry's contract.
            if on_retry is None:
                return
            # attempt_error is set only when this attempt returned Err; if
            # func() raised directly instead, fall back to the exception
            # tenacity captured for this attempt rather than an Err from a
            # previous one.
            payload = (
                attempt_error
                if attempt_error is not None
                else retry_state.outcome.exception()
                if retry_state.outcome is not None
                else None
            )
            on_retry(retry_state.attempt_number, cast(E, payload))

        try:
            for attempt in Retrying(
                stop=actual_stop,
                wait=actual_wait,
                reraise=False,
                before_sleep=_before_sleep,
            ):
                attempt_count += 1
                attempt_error = None

                # Called before entering `with attempt:` so a raised
                # exception is plain Python control flow tenacity never
                # sees - it propagates to the caller unchanged instead of
                # being treated as a retryable failure.
                if before_attempt is not None:
                    before_attempt(attempt_count)

                with attempt:
                    result = func(*args, **kwargs)
                    last_result = result

                    if result.is_err():
                        error = result.unwrap_err()
                        attempt_error = error

                        if error_types is not None and not isinstance(
                            error, error_types
                        ):
                            if log_attempts:
                                logger.debug(
                                    f"{func_name} failed with non-retryable error "
                                    f"{type(error).__name__}: {error}"
                                )
                            return result

                        if retry_if is not None and not retry_if(error):
                            if log_attempts:
                                logger.debug(
                                    f"{func_name} failed with not-retryable "
                                    f"(retry_if) error: {error}"
                                )
                            return result

                        if log_attempts:
                            if error_types is not None:
                                logger.debug(
                                    f"Attempt {attempt_count} of {func_name} failed "
                                    f"with {type(error).__name__}: {error}"
                                )
                            else:
                                logger.debug(
                                    f"Attempt {attempt_count} of {func_name} "
                                    f"failed: {error}"
                                )

                        # Convert to exception for tenacity
                        if isinstance(error, Exception):
                            raise error
                        else:
                            raise ValueError(f"Operation failed: {error}")

                    # Success case
                    if log_attempts and attempt_count > 1:
                        logger.info(
                            f"{func_name} succeeded after {attempt_count} attempts"
                        )

                    return result

        except RetryError:
            if log_attempts:
                logger.warning(f"{func_name} failed after {attempt_count} attempts")

            return (
                last_result
                if last_result is not None
                else Err.from_value("All retry attempts failed")
            )  # type: ignore

        return (
            last_result
            if last_result is not None
            else Err.from_value("Unknown retry error")
        )  # type: ignore

    return wrapper


def on_err(
    stop: Any = None,
    wait: Any = None,
    log_attempts: bool = True,
    retry_if: Callable[[E], bool] | None = None,
    before_attempt: Callable[[int], None] | None = None,
    on_retry: Callable[[int, E], None] | None = None,
) -> Callable[[Callable[..., Result[T, E]]], Callable[..., Result[T, E]]]:
    """Retry a Result-returning function when it returns Err.

    ``retry_if``, ``before_attempt``, and ``on_retry`` all key off a
    returned ``Err`` value. An exception the wrapped function *raises*
    directly (instead of returning as ``Err``) bypasses ``retry_if``
    entirely and is retried unconditionally per tenacity's default policy,
    same as before these hooks existed. Wrap the risky call with
    ``Result.of(...)`` first if you need it filtered too:
    ``Result.of(lambda: risky())`` turns a raised exception into an
    ``Err`` the hooks can see.

    Args:
        stop: Tenacity stop condition (when to stop retrying).
        wait: Tenacity wait condition (how long to wait between retries).
        log_attempts: Whether to log retry attempts.
        retry_if: Predicate on the Err value; retry only when it returns
            True. When it returns False, retrying stops immediately and
            that Err is returned (logged at DEBUG as not retryable).
            Defaults to always retrying, matching the pre-existing
            behaviour.
        before_attempt: Called before every attempt with the 1-based
            attempt number (including the first). If it raises, that
            exception propagates to the caller unchanged - it is not
            converted to an Err, not retried, and never surfaces as a
            tenacity RetryError.
        on_retry: Called with the 1-based attempt number and the Err value
            after each failed attempt that will be retried. Not called
            after the final, exhausting attempt.

    Examples:
        >>> @on_err(stop=stop_after_attempt(3))
        ... def flaky_operation() -> Result[int, str]:
        ...     return Ok(42)  # or Err("failed") sometimes

        >>> @on_err(wait=wait_fixed(1), log_attempts=True)
        ... def network_call() -> Result[str, Exception]:
        ...     return Ok("success")

        Only retry Err values that satisfy a predicate - here, retry on a
        429 status but give up immediately on anything else:

        >>> from tenacity import wait_none
        >>> @on_err(wait=wait_none(), retry_if=lambda status: status == 429)
        ... def call_api() -> Result[str, int]:
        ...     return Err(404)
        >>> call_api()
        Err(404)

        ``before_attempt``/``on_retry`` observe attempts without changing
        control flow - handy for attempt counters or budget checks:

        >>> attempts = []
        >>> @on_err(wait=wait_none(), before_attempt=attempts.append)
        ... def flaky() -> Result[int, str]:
        ...     return Ok(1) if len(attempts) >= 2 else Err("not yet")
        >>> flaky().unwrap()
        1
        >>> attempts
        [1, 2]
    """

    def decorator(func: Callable[..., Result[T, E]]) -> Callable[..., Result[T, E]]:
        return _make_retry_wrapper(
            func,
            error_types=None,
            stop=stop,
            wait=wait,
            log_attempts=log_attempts,
            retry_if=retry_if,
            before_attempt=before_attempt,
            on_retry=on_retry,
        )

    return decorator


def on_err_type(
    *error_types: type[Exception],
    stop: Any = None,
    wait: Any = None,
    log_attempts: bool = True,
    retry_if: Callable[[E], bool] | None = None,
    before_attempt: Callable[[int], None] | None = None,
    on_retry: Callable[[int, E], None] | None = None,
) -> Callable[[Callable[..., Result[T, E]]], Callable[..., Result[T, E]]]:
    """Retry only when Result contains specific exception types.

    ``error_types``, ``retry_if``, ``before_attempt``, and ``on_retry`` all
    key off a returned ``Err`` value. An exception the wrapped function
    *raises* directly (instead of returning as ``Err``) bypasses both the
    ``error_types`` check and ``retry_if`` entirely and is retried
    unconditionally per tenacity's default policy, same as before these
    hooks existed. Wrap the risky call with ``Result.of(...)`` first if you
    need it filtered too: ``Result.of(lambda: risky())`` turns a raised
    exception into an ``Err`` the checks and hooks can see.

    Args:
        error_types: Exception types that should trigger retries.
        stop: Tenacity stop condition.
        wait: Tenacity wait condition.
        log_attempts: Whether to log retry attempts.
        retry_if: Additional predicate on the Err value, applied after the
            ``error_types`` check; retry only when it returns True. Useful
            to exclude a subclass of an otherwise-retryable type. When it
            returns False, that Err is returned immediately (logged at
            DEBUG as not retryable). Defaults to always retrying (matching
            pre-existing behaviour) once ``error_types`` matches.
        before_attempt: Called before every attempt with the 1-based
            attempt number (including the first). If it raises, that
            exception propagates to the caller unchanged.
        on_retry: Called with the 1-based attempt number and the Err value
            after each failed attempt that will be retried. Not called
            after the final, exhausting attempt.

    Examples:
        >>> @on_err_type(ConnectionError, TimeoutError)
        ... def network_operation() -> Result[str, Exception]:
        ...     return Ok("success")

        Exclude a subclass from an otherwise-retryable exception type -
        retry a 429 but not the 402 that subclasses it:

        >>> from tenacity import wait_none
        >>> class TooManyRequestsError(Exception): pass
        >>> class PaymentRequiredError(TooManyRequestsError): pass
        >>> @on_err_type(
        ...     TooManyRequestsError,
        ...     wait=wait_none(),
        ...     retry_if=lambda err: not isinstance(err, PaymentRequiredError),
        ... )
        ... def call_api() -> Result[str, Exception]:
        ...     return Err(PaymentRequiredError("payment required"))
        >>> call_api().unwrap_err()
        PaymentRequiredError('payment required')
    """

    def decorator(func: Callable[..., Result[T, E]]) -> Callable[..., Result[T, E]]:
        return _make_retry_wrapper(
            func,
            error_types=error_types,
            stop=stop,
            wait=wait,
            log_attempts=log_attempts,
            retry_if=retry_if,
            before_attempt=before_attempt,
            on_retry=on_retry,
        )

    return decorator


def with_retry[T](
    func: Callable[[], T],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    log_attempts: bool = True,
) -> Result[T, Exception]:
    """Execute a function with simple retry logic, returning a Result.

    A functional utility for adding retry logic to any callable.

    Args:
        func: The function to execute with retries.
        max_attempts: Maximum number of attempts.
        delay: Base delay between retries in seconds.
        backoff: Whether to use exponential backoff.
        log_attempts: Whether to log retry attempts.

    Returns:
        Ok(result) if successful, Err(exception) if all attempts failed.

    Examples:
        >>> def might_fail():
        ...     return "success"
        >>>
        >>> result = with_retry(might_fail, max_attempts=3, delay=0.5)
        >>> if result.is_ok():
        ...     value = result.unwrap()
    """
    wait_strategy = (
        wait_exponential(multiplier=delay, min=delay, max=30)
        if backoff
        else wait_fixed(delay)
    )

    attempt_count = 0
    last_exception: Exception | None = None

    if log_attempts:
        func_name = Option.of(lambda: func.__name__).unwrap_or("callable")
        logger.debug(f"Starting retry execution of {func_name}")

    try:
        for attempt in Retrying(
            stop=stop_after_attempt(max_attempts), wait=wait_strategy, reraise=False
        ):
            with attempt:
                attempt_count += 1
                try:
                    result = func()
                    if log_attempts and attempt_count > 1:
                        logger.info(
                            f"Function succeeded after {attempt_count} attempts"
                        )
                    return Ok(result)
                except Exception as e:
                    last_exception = e
                    if log_attempts:
                        logger.debug(f"Attempt {attempt_count} failed: {e}")
                    raise

    except RetryError:
        if log_attempts:
            logger.warning(f"Function failed after {attempt_count} attempts")

        return Err.from_exception(
            last_exception or Exception("All retry attempts failed")
        )

    # Shouldn't reach here
    return Err.from_exception(last_exception or Exception("Unknown retry error"))


def until_ok[T, E](
    func: Callable[[], Result[T, E]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    log_attempts: bool = True,
) -> Result[T, E]:
    """Retry a Result-returning function until it returns Ok.

    A functional alternative to the decorator approach.

    Args:
        func: Function that returns a Result.
        max_attempts: Maximum number of attempts.
        delay: Base delay between retries.
        backoff: Whether to use exponential backoff.
        log_attempts: Whether to log attempts.

    Returns:
        The first Ok result, or the last Err if all attempts fail.

    Examples:
        >>> def flaky_operation() -> Result[int, str]:
        ...     return Ok(42)  # or sometimes Err("failed")
        >>>
        >>> final_result = until_ok(flaky_operation, max_attempts=5)
    """
    wait_strategy = (
        wait_exponential(multiplier=delay, min=delay, max=30)
        if backoff
        else wait_fixed(delay)
    )

    attempt_count = 0
    last_result: Result[T, E] | None = None

    if log_attempts:
        func_name = Option.of(lambda: func.__name__).unwrap_or("callable")
        logger.debug(f"Starting retry execution of {func_name}")

    try:
        for attempt in Retrying(
            stop=stop_after_attempt(max_attempts), wait=wait_strategy, reraise=False
        ):
            with attempt:
                attempt_count += 1
                result = func()
                last_result = result

                if result.is_ok():
                    if log_attempts and attempt_count > 1:
                        func_name = Option.of(lambda: func.__name__).unwrap_or(
                            "callable"
                        )
                        logger.info(
                            f"{func_name} succeeded after {attempt_count} attempts"
                        )
                    return result
                else:
                    error = result.unwrap_err()
                    if log_attempts:
                        logger.debug(f"Attempt {attempt_count} returned Err: {error}")

                    # Create an exception to trigger tenacity retry
                    if isinstance(error, Exception):
                        raise error
                    else:
                        raise ValueError(f"Operation returned Err: {error}")

    except RetryError:
        if log_attempts:
            func_name = Option.of(lambda: func.__name__).unwrap_or("callable")
            logger.warning(f"{func_name} failed after {attempt_count} attempts")

        return (
            last_result
            if last_result is not None
            else Err.from_value("All retry attempts failed")
        )  # type: ignore

    return (
        last_result
        if last_result is not None
        else Err.from_value("Unknown retry error")
    )  # type: ignore


# Convenience functions for common retry patterns
def quick[T](func: Callable[[], T]) -> Result[T, Exception]:
    """Quick retry with 2 attempts and minimal delay."""
    return with_retry(func, max_attempts=2, delay=0.1, backoff=False)


def standard[T](func: Callable[[], T]) -> Result[T, Exception]:
    """Standard retry with exponential backoff."""
    return with_retry(func, max_attempts=3, delay=1.0, backoff=True)


def persistent[T](func: Callable[[], T]) -> Result[T, Exception]:
    """Persistent retry for important operations."""
    return with_retry(func, max_attempts=10, delay=2.0, backoff=True)


def retry_if_err(
    result: Result[T, E],
    func: Callable[[], Result[T, E]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: bool = True,
    log_attempts: bool = True,
) -> Result[T, E]:
    """Retry the provided function if the given Result is an Err.

    If ``result`` is Ok, it is returned immediately without calling ``func``.
    Otherwise ``func`` is retried using the same semantics as :func:`until_ok`.

    This is a plain functional alternative to attaching a ``.retry()`` method
    onto the core ``Result`` type: it is only available when explicitly
    imported from ``logerr.recipes.retry``, keeping optional functionality out
    of the core API surface.

    Args:
        result: The Result to check; retried only if it is Err.
        func: Function to retry if ``result`` is Err.
        max_attempts: Maximum retry attempts.
        delay: Base delay between retries.
        backoff: Whether to use exponential backoff.
        log_attempts: Whether to log attempts.

    Returns:
        ``result`` if it is Ok, otherwise the result of retrying ``func``.

    Examples:
        >>> result = Err("original error")
        >>> final_result = retry_if_err(result, lambda: Ok(42))
        >>> final_result.unwrap()
        42
    """
    if result.is_ok():
        return result

    return until_ok(func, max_attempts, delay, backoff, log_attempts)
