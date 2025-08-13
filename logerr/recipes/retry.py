"""
Functional retry patterns for Result types with automatic logging.

This module provides lightweight, functional retry patterns that integrate with
Result types and automatically log retry attempts using loguru.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from loguru import logger
from tenacity import (  # type: ignore[import-not-found]
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


def on_err(
    stop: Any = None,
    wait: Any = None,
    log_attempts: bool = True,
) -> Callable[[Callable[..., Result[T, E]]], Callable[..., Result[T, E]]]:
    """Retry a Result-returning function when it returns Err.

    Args:
        stop: Tenacity stop condition (when to stop retrying).
        wait: Tenacity wait condition (how long to wait between retries).
        log_attempts: Whether to log retry attempts.

    Examples:
        >>> @on_err(stop=stop_after_attempt(3))
        ... def flaky_operation() -> Result[int, str]:
        ...     return Ok(42)  # or Err("failed") sometimes

        >>> @on_err(wait=wait_fixed(1), log_attempts=True)
        ... def network_call() -> Result[str, Exception]:
        ...     return Ok("success")
    """

    def decorator(func: Callable[..., Result[T, E]]) -> Callable[..., Result[T, E]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Result[T, E]:
            last_result: Result[T, E] | None = None
            attempt_count = 0

            # Use functional API for parameter defaults

            actual_stop = Option.from_nullable(stop).unwrap_or_else(
                lambda: stop_after_attempt(3)
            )
            actual_wait = Option.from_nullable(wait).unwrap_or_else(
                lambda: wait_exponential(multiplier=1, min=4, max=10)
            )

            if log_attempts:
                func_name = Option.of(lambda: func.__name__).unwrap_or("callable")
                logger.debug(f"Starting retry operation for {func_name}")

            try:
                for attempt in Retrying(
                    stop=actual_stop, wait=actual_wait, reraise=False
                ):
                    with attempt:
                        attempt_count += 1
                        result = func(*args, **kwargs)
                        last_result = result

                        if result.is_err():
                            if log_attempts:
                                error_msg = getattr(result, "_error", "unknown error")
                                logger.debug(
                                    f"Attempt {attempt_count} of {func_name} failed: {error_msg}"
                                )

                            # Convert to exception for tenacity
                            if hasattr(result, "_error"):
                                error = result._error  # type: ignore
                                if isinstance(error, Exception):
                                    raise error
                                else:
                                    raise ValueError(f"Operation failed: {error}")
                            else:
                                raise ValueError("Operation failed")

                        # Success case
                        if log_attempts and attempt_count > 1:
                            logger.info(
                                f"{func_name} succeeded after {attempt_count} attempts"
                            )

                        return result

            except RetryError:
                if log_attempts:
                    logger.warning(f"{func_name} failed after {attempt_count} attempts")

                return last_result or Err.from_value("All retry attempts failed")  # type: ignore

            return last_result or Err.from_value("Unknown retry error")  # type: ignore

        return wrapper

    return decorator


def on_err_type(
    *error_types: type[Exception],
    stop: Any = None,
    wait: Any = None,
    log_attempts: bool = True,
) -> Callable[[Callable[..., Result[T, E]]], Callable[..., Result[T, E]]]:
    """Retry only when Result contains specific exception types.

    Args:
        error_types: Exception types that should trigger retries.
        stop: Tenacity stop condition.
        wait: Tenacity wait condition.
        log_attempts: Whether to log retry attempts.

    Examples:
        >>> @on_err_type(ConnectionError, TimeoutError)
        ... def network_operation() -> Result[str, Exception]:
        ...     return Ok("success")
    """

    def decorator(func: Callable[..., Result[T, E]]) -> Callable[..., Result[T, E]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Result[T, E]:
            last_result: Result[T, E] | None = None
            attempt_count = 0

            # Use functional API for parameter defaults

            actual_stop = Option.from_nullable(stop).unwrap_or_else(
                lambda: stop_after_attempt(3)
            )
            actual_wait = Option.from_nullable(wait).unwrap_or_else(
                lambda: wait_exponential(multiplier=1, min=4, max=10)
            )

            if log_attempts:
                func_name = Option.of(lambda: func.__name__).unwrap_or("callable")
                logger.debug(
                    f"Starting retry operation for {func_name} (retrying on: {error_types})"
                )

            try:
                for attempt in Retrying(
                    stop=actual_stop, wait=actual_wait, reraise=False
                ):
                    with attempt:
                        attempt_count += 1
                        result = func(*args, **kwargs)
                        last_result = result

                        if result.is_err() and hasattr(result, "_error"):
                            error = result._error  # type: ignore

                            # Only retry if error is one of the specified types
                            if isinstance(error, error_types):
                                if log_attempts:
                                    logger.debug(
                                        f"Attempt {attempt_count} of {func_name} failed with {type(error).__name__}: {error}"
                                    )
                                raise error
                            else:
                                # Don't retry this error type
                                if log_attempts:
                                    logger.debug(
                                        f"{func_name} failed with non-retryable error {type(error).__name__}: {error}"
                                    )
                                return result

                        # Success case or non-retryable error
                        if log_attempts and attempt_count > 1:
                            logger.info(
                                f"{func_name} succeeded after {attempt_count} attempts"
                            )

                        return result

            except RetryError:
                if log_attempts:
                    logger.warning(f"{func_name} failed after {attempt_count} attempts")

                return last_result or Err.from_value("All retry attempts failed")  # type: ignore

            return last_result or Err.from_value("Unknown retry error")  # type: ignore

        return wrapper

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
                    if log_attempts:
                        error_msg = getattr(result, "_error", "unknown error")
                        logger.debug(
                            f"Attempt {attempt_count} returned Err: {error_msg}"
                        )

                    # Create an exception to trigger tenacity retry
                    if hasattr(result, "_error"):
                        error = result._error  # type: ignore
                        if isinstance(error, Exception):
                            raise error
                        else:
                            raise ValueError(f"Operation returned Err: {error}")
                    else:
                        raise ValueError("Operation returned Err")

    except RetryError:
        if log_attempts:
            func_name = Option.of(lambda: func.__name__).unwrap_or("callable")
            logger.warning(f"{func_name} failed after {attempt_count} attempts")

        return last_result or Err.from_value("All retry attempts failed")  # type: ignore

    return last_result or Err.from_value("Unknown retry error")  # type: ignore


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


# Method to add retry capability to existing Results
def _add_retry_method() -> None:
    """Add retry method to Result base class."""

    def retry(
        self: Result[T, E],
        func: Callable[[], Result[T, E]],
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: bool = True,
        log_attempts: bool = True,
    ) -> Result[T, E]:
        """Retry the provided function if this Result is an Err.

        If this Result is Ok, return it immediately. Otherwise, retry the function.

        Args:
            func: Function to retry if this is Err.
            max_attempts: Maximum retry attempts.
            delay: Base delay between retries.
            backoff: Whether to use exponential backoff.
            log_attempts: Whether to log attempts.

        Returns:
            This Result if Ok, otherwise the result of retrying func.

        Examples:
            >>> result = some_operation()
            >>> final_result = result.retry(lambda: fallback_operation())
        """
        if self.is_ok():
            return self

        return until_ok(func, max_attempts, delay, backoff, log_attempts)

    # Add the method to the Result class
    from ..result import Result

    Result.retry = retry  # type: ignore


# Initialize the retry method on import
_add_retry_method()
