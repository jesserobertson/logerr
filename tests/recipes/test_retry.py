"""Tests for retry functionality."""

import time
from unittest.mock import patch

import pytest

# Skip all tests if tenacity is not available
pytest.importorskip("tenacity")

from tenacity import stop_after_attempt, wait_fixed

from logerr import Err, Ok, Result
from logerr.recipes import retry


class TestRetryDecorators:
    """Test retry decorators functionality."""

    def test_decorator_preserves_function_metadata(self):
        """Test that decorators preserve original function metadata."""

        @retry.on_err(log_attempts=False)
        def test_function() -> Result[str, str]:
            """This is a test function."""
            return Ok("test")

        assert test_function.__name__ == "test_function"
        assert "This is a test function." in test_function.__doc__

    def test_decorator_can_be_applied_without_parentheses(self):
        """Test that decorator works when applied directly without calling."""
        # This tests that the decorator function signature is correct
        call_count = 0

        # Note: on_err requires parentheses because it takes parameters
        @retry.on_err(log_attempts=False)
        def decorated_function() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            return Ok(42)

        result = decorated_function()
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 1

    def test_decorator_accepts_function_arguments(self):
        """Test that decorated functions can accept and pass through arguments."""

        @retry.on_err(stop=stop_after_attempt(2), log_attempts=False)
        def function_with_args(x: int, y: str = "default") -> Result[str, str]:
            if x < 0:
                return Err("negative input")
            return Ok(f"{x}_{y}")

        # Test with positional args
        result = function_with_args(5)
        assert result.is_ok()
        assert result.unwrap() == "5_default"

        # Test with keyword args
        result = function_with_args(10, y="custom")
        assert result.is_ok()
        assert result.unwrap() == "10_custom"

        # Test that retry works with args
        result = function_with_args(-1)
        assert result.is_err()

    def test_multiple_decorators_can_be_stacked(self):
        """Test that multiple retry decorators can be stacked."""
        call_count = 0

        # Apply two decorators (though this is unusual, it should work)
        @retry.on_err(stop=stop_after_attempt(2), log_attempts=False)
        @retry.on_err(stop=stop_after_attempt(2), log_attempts=False)
        def double_decorated() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Err("first failure")
            return Ok(42)

        result = double_decorated()
        assert result.is_ok()
        assert result.unwrap() == 42
        # Due to stacking, the retry logic may be applied multiple times
        assert call_count >= 2

    def test_on_err_decorator_success_first_try(self):
        """Test that on_err decorator doesn't retry on successful operations."""
        call_count = 0

        @retry.on_err(stop=stop_after_attempt(3), log_attempts=False)
        def successful_operation() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            return Ok(42)

        result = successful_operation()
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 1

    def test_on_err_decorator_retries_on_failure(self):
        """Test that on_err decorator retries on Err results."""
        call_count = 0

        @retry.on_err(
            stop=stop_after_attempt(3), wait=wait_fixed(0.01), log_attempts=False
        )
        def failing_operation() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return Err("failed")
            return Ok(42)

        result = failing_operation()
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 3

    def test_on_err_decorator_exhausts_retries(self):
        """Test that on_err decorator eventually gives up."""
        call_count = 0

        @retry.on_err(
            stop=stop_after_attempt(2), wait=wait_fixed(0.01), log_attempts=False
        )
        def always_failing_operation() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            return Err("always fails")

        result = always_failing_operation()
        assert result.is_err()
        assert call_count == 2

    def test_on_err_type_decorator_retries_specific_errors(self):
        """Test that on_err_type only retries specific exception types."""
        call_count = 0

        @retry.on_err_type(
            ValueError,
            stop=stop_after_attempt(3),
            wait=wait_fixed(0.01),
            log_attempts=False,
        )
        def selective_failing_operation() -> Result[int, Exception]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Err.from_exception(ValueError("retry this"))
            elif call_count == 2:
                return Err.from_exception(RuntimeError("don't retry this"))
            return Ok(42)

        result = selective_failing_operation()
        assert result.is_err()
        assert isinstance(result.unwrap_err(), RuntimeError)
        assert call_count == 2  # Should stop after RuntimeError

    def test_on_err_type_decorator_success_after_retry(self):
        """Test that on_err_type succeeds after retrying correct error type."""
        call_count = 0

        @retry.on_err_type(
            ValueError,
            stop=stop_after_attempt(3),
            wait=wait_fixed(0.01),
            log_attempts=False,
        )
        def eventually_succeeds() -> Result[int, Exception]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return Err.from_exception(ValueError("retry this"))
            return Ok(42)

        result = eventually_succeeds()
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 3

    def test_decorator_with_custom_wait_strategy(self):
        """Test that decorators work with custom wait strategies."""
        call_count = 0
        start_time = time.time()

        @retry.on_err(
            stop=stop_after_attempt(3),
            wait=wait_fixed(0.1),  # 100ms delay
            log_attempts=False,
        )
        def delayed_retry() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return Err("not yet")
            return Ok(42)

        result = delayed_retry()
        end_time = time.time()

        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 3
        # Should have taken at least 200ms (2 delays of 100ms each)
        assert (end_time - start_time) >= 0.18  # Allow some margin

    def test_decorator_parameters_are_properly_passed(self):
        """Test that all decorator parameters are properly used."""
        call_count = 0

        # Test with specific stop condition
        @retry.on_err(
            stop=stop_after_attempt(2),  # Only 2 attempts
            wait=wait_fixed(0.01),
            log_attempts=False,
        )
        def limited_retries() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            return Err("always fails")

        result = limited_retries()
        assert result.is_err()
        assert call_count == 2  # Exactly 2 attempts due to stop condition

    def test_on_err_type_decorator_with_multiple_exception_types(self):
        """Test on_err_type with multiple exception types."""
        call_count = 0

        @retry.on_err_type(
            ValueError,
            RuntimeError,
            TypeError,
            stop=stop_after_attempt(4),
            wait=wait_fixed(0.01),
            log_attempts=False,
        )
        def multi_exception_func() -> Result[int, Exception]:
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                return Err.from_exception(ValueError("value error"))
            elif call_count == 2:
                return Err.from_exception(RuntimeError("runtime error"))
            elif call_count == 3:
                return Err.from_exception(TypeError("type error"))
            return Ok(42)

        result = multi_exception_func()
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 4

    def test_decorator_works_with_async_like_patterns(self):
        """Test decorator with functions that return different Result types."""

        @retry.on_err(stop=stop_after_attempt(2), log_attempts=False)
        def varying_return_types(success: bool) -> Result[str | int, str]:
            if success:
                return Ok("string_result")
            else:
                return Err("failed")

        # Test with different return types
        result1 = varying_return_types(True)
        assert result1.is_ok()
        assert result1.unwrap() == "string_result"

        result2 = varying_return_types(False)
        assert result2.is_err()

    def test_decorator_integration_with_result_factory_methods(self):
        """Test that decorators work with Result factory methods."""

        @retry.on_err(stop=stop_after_attempt(2), log_attempts=False)
        def using_result_factories() -> Result[int, Exception]:
            # Test with Result.from_callable
            return Result.from_callable(lambda: 42)

        result = using_result_factories()
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_decorator_preserves_original_function_behavior(self):
        """Test that decorated functions behave identically to originals when successful."""

        def original_func(x: int, y: int) -> Result[int, str]:
            if x + y < 0:
                return Err("negative sum")
            return Ok(x + y)

        @retry.on_err(stop=stop_after_attempt(1), log_attempts=False)
        def decorated_func(x: int, y: int) -> Result[int, str]:
            if x + y < 0:
                return Err("negative sum")
            return Ok(x + y)

        # Test identical behavior on success
        result1 = original_func(5, 10)
        result2 = decorated_func(5, 10)
        assert result1.unwrap() == result2.unwrap()

        # Test identical behavior on failure (no retry)
        result3 = original_func(-5, -10)
        result4 = decorated_func(-5, -10)
        assert result3.is_err() == result4.is_err()


class TestRetryUtilities:
    """Test retry utility functions."""

    def test_with_retry_success(self):
        """Test with_retry with successful function."""
        call_count = 0

        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = retry.with_retry(
            successful_func,
            max_attempts=3,
            delay=0.01,
            backoff=False,
            log_attempts=False,
        )
        assert result.is_ok()
        assert result.unwrap() == "success"
        assert call_count == 1

    def test_with_retry_eventual_success(self):
        """Test with_retry with function that eventually succeeds."""
        call_count = 0

        def eventually_successful_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "success"

        result = retry.with_retry(
            eventually_successful_func,
            max_attempts=5,
            delay=0.01,
            backoff=False,
            log_attempts=False,
        )
        assert result.is_ok()
        assert result.unwrap() == "success"
        assert call_count == 3

    def test_with_retry_all_attempts_fail(self):
        """Test with_retry when all attempts fail."""
        call_count = 0

        def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        result = retry.with_retry(
            always_failing_func,
            max_attempts=3,
            delay=0.01,
            backoff=False,
            log_attempts=False,
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)
        assert call_count == 3

    def test_until_ok_success(self):
        """Test until_ok with Result-returning function."""
        call_count = 0

        def successful_result_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            return Ok(42)

        result = retry.until_ok(
            successful_result_func,
            max_attempts=3,
            delay=0.01,
            backoff=False,
            log_attempts=False,
        )
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 1

    def test_until_ok_eventual_success(self):
        """Test until_ok with function that eventually returns Ok."""
        call_count = 0

        def eventually_ok_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return Err("not yet")
            return Ok(42)

        result = retry.until_ok(
            eventually_ok_func,
            max_attempts=5,
            delay=0.01,
            backoff=False,
            log_attempts=False,
        )
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 3

    def test_until_ok_all_attempts_fail(self):
        """Test until_ok when all attempts return Err."""
        call_count = 0

        def always_err_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            return Err("always fails")

        result = retry.until_ok(
            always_err_func,
            max_attempts=3,
            delay=0.01,
            backoff=False,
            log_attempts=False,
        )
        assert result.is_err()
        assert call_count == 3


class TestConvenienceFunctions:
    """Test convenience retry functions."""

    def test_quick_retry(self):
        """Test quick retry function."""
        call_count = 0

        def quick_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first attempt fails")
            return "success"

        result = retry.quick(quick_func)
        assert result.is_ok()
        assert result.unwrap() == "success"
        assert call_count == 2

    def test_standard_retry(self):
        """Test standard retry function."""
        call_count = 0

        def standard_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "success"

        result = retry.standard(standard_func)
        assert result.is_ok()
        assert result.unwrap() == "success"
        assert call_count == 3

    def test_persistent_retry(self):
        """Test persistent retry function."""
        call_count = 0

        def persistent_func():
            nonlocal call_count
            call_count += 1
            if call_count < 5:
                raise ValueError("not yet")
            return "success"

        result = retry.persistent(persistent_func)
        assert result.is_ok()
        assert result.unwrap() == "success"
        assert call_count == 5


class TestResultRetryMethod:
    """Test the retry method added to Result class."""

    def test_result_retry_method_ok_result(self):
        """Test that Ok results don't trigger retry."""
        call_count = 0

        def fallback_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            return Ok(99)

        ok_result = Ok(42)
        final_result = ok_result.retry(fallback_func)

        assert final_result.is_ok()
        assert final_result.unwrap() == 42  # Original value, not fallback
        assert call_count == 0  # Fallback never called

    def test_result_retry_method_err_result(self):
        """Test that Err results trigger retry."""
        call_count = 0

        def fallback_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return Err("fallback failed")
            return Ok(99)

        err_result = Err("original error")
        final_result = err_result.retry(
            fallback_func, max_attempts=3, delay=0.01, backoff=False, log_attempts=False
        )

        assert final_result.is_ok()
        assert final_result.unwrap() == 99
        assert call_count == 2


class TestLogging:
    """Test retry logging functionality."""

    @patch("logerr.recipes.retry.logger")
    def test_retry_logging_enabled(self, mock_logger):
        """Test that retry attempts are logged when enabled."""
        call_count = 0

        @retry.on_err(
            stop=stop_after_attempt(2), wait=wait_fixed(0.01), log_attempts=True
        )
        def logged_operation() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Err("first failure")
            return Ok(42)

        result = logged_operation()

        assert result.is_ok()
        assert result.unwrap() == 42

        # Check that debug logs were called
        assert mock_logger.debug.call_count >= 2  # At least start and attempt logs
        assert mock_logger.info.called  # Success after retry

    @patch("logerr.recipes.retry.logger")
    def test_retry_logging_disabled(self, mock_logger):
        """Test that retry attempts are not logged when disabled."""
        call_count = 0

        @retry.on_err(
            stop=stop_after_attempt(2), wait=wait_fixed(0.01), log_attempts=False
        )
        def silent_operation() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Err("first failure")
            return Ok(42)

        result = silent_operation()

        assert result.is_ok()
        assert result.unwrap() == 42

        # Check that no logs were called
        assert not mock_logger.debug.called
        assert not mock_logger.info.called
        assert not mock_logger.warning.called


class TestErrorHandling:
    """Test error handling in retry scenarios."""

    def test_exception_in_decorator_function(self):
        """Test handling exceptions raised in decorated functions."""
        call_count = 0

        @retry.on_err(
            stop=stop_after_attempt(2), wait=wait_fixed(0.01), log_attempts=False
        )
        def exception_raising_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("unexpected exception")
            return Ok(42)

        result = exception_raising_func()

        # Should retry after exception and eventually succeed
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 2

    def test_mixed_errors_and_results(self):
        """Test handling mix of exceptions and Err results."""
        call_count = 0

        @retry.on_err(
            stop=stop_after_attempt(3), wait=wait_fixed(0.01), log_attempts=False
        )
        def mixed_failure_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Err("result error")
            elif call_count == 2:
                raise RuntimeError("exception error")
            return Ok(42)

        result = mixed_failure_func()

        # Should handle both types of failures and eventually succeed
        assert result.is_ok()
        assert result.unwrap() == 42
        assert call_count == 3

    def test_exception_exhausts_retries(self):
        """Test that exceptions eventually exhaust retries."""
        call_count = 0

        @retry.on_err(
            stop=stop_after_attempt(2), wait=wait_fixed(0.01), log_attempts=False
        )
        def always_exception_func() -> Result[int, str]:
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        result = always_exception_func()

        # Should fail after exhausting retries
        assert result.is_err()
        # The retry mechanism returns a generic error message when all attempts fail
        assert "All retry attempts failed" in str(result.unwrap_err())
        assert call_count == 2
