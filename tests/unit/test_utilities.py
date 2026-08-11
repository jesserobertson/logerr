"""
Tests for utility functions in logerr.utilities module.
"""

import pytest

from logerr import Err, Nothing, Ok, Some
from logerr.utilities import (
    attribute,
    chain,
    error,
    execute,
    log,
    nullable,
    pipe,
    resolve,
    try_chain,
    validate,
    wrap_option,
    wrap_result,
)

pytestmark = pytest.mark.unit


class TestExecute:
    """Test the execute utility function."""

    def test_execute_success_result(self):
        """Test execute with successful operation returning Result."""
        result = execute(lambda: 42)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_execute_exception_result(self):
        """Test execute with exception returning Result."""
        result = execute(lambda: 1 / 0)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ZeroDivisionError)

    def test_execute_success_option(self):
        """Test execute with successful operation returning Option."""
        result = execute(lambda: "hello", return_type="option")
        assert result.is_some()
        assert result.unwrap() == "hello"

    def test_execute_none_result_option(self):
        """Test execute when callable returns None for option mode."""
        result = execute(lambda: None, return_type="option")
        assert result.is_nothing()

    def test_execute_exception_option(self):
        """Test execute with exception returning Option."""
        result = execute(lambda: 1 / 0, return_type="option")
        assert result.is_nothing()

    def test_execute_falsy_default_error_zero(self):
        """A falsy default_error (0) must still be honored, not discarded via `or`."""
        result = execute(lambda: 1 / 0, default_error=0)
        assert result.is_err()
        assert result.unwrap_err() == 0

    def test_execute_falsy_default_error_empty_string(self):
        """A falsy default_error ("") must still be honored, not discarded via `or`."""
        result = execute(lambda: 1 / 0, default_error="")
        assert result.is_err()
        assert result.unwrap_err() == ""

    def test_execute_falsy_default_error_false(self):
        """A falsy default_error (False) must still be honored, not discarded via `or`."""
        result = execute(lambda: 1 / 0, default_error=False)
        assert result.is_err()
        assert result.unwrap_err() is False

    def test_execute_no_default_error_uses_exception(self):
        """When default_error is not provided, the caught exception is used."""
        result = execute(lambda: 1 / 0)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ZeroDivisionError)


class TestNullable:
    """Test the nullable utility function."""

    def test_nullable_some_value_option(self):
        """Test nullable with a non-None value returning Option."""
        result = nullable("test")
        assert result.is_some()
        assert result.unwrap() == "test"

    def test_nullable_none_value_option(self):
        """Test nullable with None value returning Option."""
        result = nullable(None)
        assert result.is_nothing()

    def test_nullable_some_value_result(self):
        """Test nullable with non-None value returning Result."""
        result = nullable("test", return_type="result")
        assert result.is_ok()
        assert result.unwrap() == "test"

    def test_nullable_none_value_result(self):
        """Test nullable with None value returning Result."""
        result = nullable(None, return_type="result")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_nullable_custom_error_factory(self):
        """Test nullable with custom error factory."""
        result = nullable(
            None, return_type="result", error_factory=lambda: RuntimeError("custom")
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), RuntimeError)
        assert str(result.unwrap_err()) == "custom"

    def test_nullable_error_factory_non_callable_value(self):
        """Test nullable with a plain (non-callable) error value, not a factory."""
        result = nullable(None, return_type="result", error_factory="plain error")
        assert result.is_err()
        assert result.unwrap_err() == "plain error"

    def test_nullable_none_value_option_log_disabled(self):
        """Test nullable with None value and log_absence disabled."""
        result = nullable(None, log_absence=False)
        assert result.is_nothing()

    def test_nullable_none_value_option_log_disabled_does_not_log(self):
        """log_absence=False must actually suppress logging, not just still work."""
        from unittest.mock import patch

        from logerr.option import logger as option_logger

        with patch.object(option_logger, "bind") as mock_bind:
            nullable(None, log_absence=False)
        mock_bind.assert_not_called()

    def test_nullable_none_value_result_log_disabled_does_not_log(self):
        """log_absence=False must be honored for the Result branch too, not just Option."""
        from unittest.mock import patch

        from logerr.result import logger as result_logger

        with patch.object(result_logger, "bind") as mock_bind:
            result = nullable(None, return_type="result", log_absence=False)
        assert result.is_err()
        mock_bind.assert_not_called()


class TestLogHelper:
    """Additional coverage for the log() utility's disabled-logging branch."""

    def test_log_noop_when_logging_disabled(self):
        from logerr import configure, reset_config

        configure(enabled=False)
        try:
            # Should return without raising, exercising the early-return branch.
            log("Should not be logged")
        finally:
            reset_config()


class TestLog:
    """Test the log utility function."""

    def test_log_with_context(self):
        """Test log function with extra context."""
        # This is more of a smoke test since we can't easily capture loguru output
        log("Test message", extra_context={"key": "value"})
        # Should not raise exception

    def test_log_different_levels(self):
        """Test log function with different log levels."""
        log("Debug message", log_level="DEBUG")
        log("Info message", log_level="INFO")
        log("Warning message", log_level="WARNING")
        log("Error message", log_level="ERROR")
        # Should not raise exceptions


class TestValidate:
    """Test the validate utility function."""

    def test_validate_passing_predicate_result(self):
        """Test validate with passing predicate returning Result."""
        result = validate(5, lambda x: x > 0, error_factory=ValueError("negative"))
        assert result.is_ok()
        assert result.unwrap() == 5

    def test_validate_failing_predicate_result(self):
        """Test validate with failing predicate returning Result."""
        result = validate(-1, lambda x: x > 0, error_factory=ValueError("negative"))
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)

    def test_validate_passing_predicate_option(self):
        """Test validate with passing predicate returning Option."""
        result = validate(
            5,
            lambda x: x > 0,
            error_factory=ValueError("negative"),
            return_type="option",
        )
        assert result.is_some()
        assert result.unwrap() == 5

    def test_validate_failing_predicate_option(self):
        """Test validate with failing predicate returning Option."""
        result = validate(
            -1,
            lambda x: x > 0,
            error_factory=ValueError("negative"),
            return_type="option",
        )
        assert result.is_nothing()

    def test_validate_exception_in_predicate(self):
        """Test validate when predicate raises exception."""
        result = validate(
            "text",
            lambda x: int(x),
            error_factory=ValueError("failed"),
            capture_exceptions=True,
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)


class TestResolveDefaults:
    """Test the resolve utility function."""

    def test_resolve_with_provided_value(self):
        """Test resolve when provided value is not None."""
        result = resolve(42, 100)
        assert result == 42

    def test_resolve_with_none_uses_default(self):
        """Test resolve when provided value is None."""
        result = resolve(None, 100)
        assert result == 100

    def test_resolve_with_validator_passing(self):
        """Test resolve with validator that passes."""
        result = resolve(50, 100, validator=lambda x: x > 0)
        assert result == 50

    def test_resolve_with_validator_failing(self):
        """Test resolve with validator that fails."""
        with pytest.raises(ValueError, match="failed validation"):
            resolve(-10, 100, validator=lambda x: x > 0)


class TestAttribute:
    """Test the attribute utility function."""

    def test_attribute_exists(self):
        """Test getting an attribute that exists."""
        result = attribute(len, "__name__", "unknown")
        assert result == "len"

    def test_attribute_missing(self):
        """Test getting an attribute that doesn't exist."""
        result = attribute(42, "__name__", "unknown")
        assert result == "unknown"

    def test_attribute_with_different_default(self):
        """Test getting attribute with different default value."""
        result = attribute(42, "nonexistent", "fallback")
        assert result == "fallback"


class TestError:
    """Test the error utility function."""

    def test_error_without_valid_options(self):
        """Test error function without valid options."""
        err = error("invalid_value", "test constraint")
        assert isinstance(err, ValueError)
        assert "Invalid test constraint: 'invalid_value'" in str(err)

    def test_error_with_valid_options(self):
        """Test error function with valid options."""
        valid_options = {"option1", "option2", "option3"}
        err = error("invalid", "choice", valid_options)
        assert isinstance(err, ValueError)
        assert "Must be one of:" in str(err)
        assert "option1" in str(err)


class TestPipe:
    """Test the pipe utility function."""

    def test_pipe_single_function(self):
        """Test pipe with a single function."""
        result = pipe("hello", str.upper)
        assert result.is_ok()
        assert result.unwrap() == "HELLO"

    def test_pipe_multiple_functions(self):
        """Test pipe with multiple functions."""
        result = pipe("  hello world  ", str.strip, str.upper, lambda s: s.split())
        assert result.is_ok()
        assert result.unwrap() == ["HELLO", "WORLD"]

    def test_pipe_no_functions(self):
        """Test pipe with no functions."""
        result = pipe("hello")
        assert result.is_ok()
        assert result.unwrap() == "hello"

    def test_pipe_short_circuits_on_failure(self):
        """A raising step returns Err immediately; later steps never run."""
        calls = []

        def track(x):
            calls.append(x)
            return x

        def fail(x):
            raise ValueError("boom")

        result = pipe("start", track, fail, track)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)
        assert calls == ["start"]  # second `track` never called


class TestTryChain:
    """Test the try_chain utility function."""

    def test_try_chain_first_succeeds(self):
        """Test try_chain when first callable succeeds."""
        result = try_chain(
            lambda: 42,
            lambda: 1 / 0,  # Would fail
        )
        assert result.is_some()
        assert result.unwrap() == 42

    def test_try_chain_second_succeeds(self):
        """Test try_chain when second callable succeeds."""
        result = try_chain(
            lambda: 1 / 0,  # Fails
            lambda: 42,
        )
        assert result.is_some()
        assert result.unwrap() == 42

    def test_try_chain_all_fail(self):
        """Test try_chain when all callables fail."""
        result = try_chain(lambda: 1 / 0, lambda: int("invalid"), lambda: [][0])
        assert result.is_nothing()


class TestChain:
    """Test the chain utility function."""

    def test_chain_success(self):
        """Test chain with successful operation."""
        result = chain(
            "42",
            int,
            error_wrapper=lambda e: Nothing.from_exception(e),
            success_wrapper=Some,
        )
        assert result.is_some()
        assert result.unwrap() == 42

    def test_chain_exception(self):
        """Test chain with operation that raises exception."""
        result = chain(
            "invalid",
            int,
            error_wrapper=lambda e: Nothing.from_exception(e),
            success_wrapper=Some,
        )
        assert result.is_nothing()


class TestWrapResult:
    """Test the wrap_result decorator."""

    def test_wrap_result_raw_value_becomes_ok(self):
        """A plain return value is wrapped as Ok."""

        @wrap_result
        def f():
            return 42

        result = f()
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_wrap_result_passes_through_ok(self):
        """A returned Ok is passed through unchanged, not re-wrapped."""

        @wrap_result
        def f():
            return Ok(42)

        result = f()
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_wrap_result_passes_through_err_without_rewrap(self):
        """A returned Err is passed through unchanged - no unwrap_err/rewrap needed."""
        inner_err = Err.from_value("boom")

        @wrap_result
        def f():
            return inner_err

        result = f()
        assert result.is_err()
        assert result is inner_err

    def test_wrap_result_exception_becomes_err(self):
        """A raised exception is caught and converted to Err."""

        @wrap_result
        def f():
            raise ValueError("bad input")

        result = f()
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)
        assert str(result.unwrap_err()) == "bad input"

    def test_wrap_result_preserves_function_name(self):
        """functools.wraps preserves __name__, matching on_err's convention."""

        @wrap_result
        def my_named_function():
            return 1

        assert my_named_function.__name__ == "my_named_function"

    def test_wrap_result_passes_args_and_kwargs(self):
        """Decorated function still receives its original arguments."""

        @wrap_result
        def add(a, b, *, c=0):
            return a + b + c

        result = add(1, 2, c=3)
        assert result.is_ok()
        assert result.unwrap() == 6

    def test_wrap_result_base_exception_propagates(self):
        """A BaseException that isn't an Exception (e.g. KeyboardInterrupt)
        propagates rather than being converted to Err - only `except Exception`
        is caught, so control-flow signals and bugs aren't silently masked."""

        class _Signal(BaseException):
            pass

        @wrap_result
        def f():
            raise _Signal("interrupted")

        with pytest.raises(_Signal):
            f()


class TestWrapOption:
    """Test the wrap_option decorator."""

    def test_wrap_option_raw_value_becomes_some(self):
        """A plain non-None return value is wrapped as Some."""

        @wrap_option
        def f():
            return 42

        result = f()
        assert result.is_some()
        assert result.unwrap() == 42

    def test_wrap_option_none_becomes_nothing(self):
        """A plain None return value becomes Nothing."""

        @wrap_option
        def f():
            return None

        result = f()
        assert result.is_nothing()

    def test_wrap_option_passes_through_some(self):
        """A returned Some is passed through unchanged, not re-wrapped."""

        @wrap_option
        def f():
            return Some(42)

        result = f()
        assert result.is_some()
        assert result.unwrap() == 42

    def test_wrap_option_passes_through_nothing(self):
        """A returned Nothing is passed through unchanged."""
        inner_nothing = Nothing.from_none("no value")

        @wrap_option
        def f():
            return inner_nothing

        result = f()
        assert result.is_nothing()
        assert result is inner_nothing

    def test_wrap_option_passes_through_some_none(self):
        """A returned Some(None) is passed through unchanged, not treated as
        the raw-None case - distinguishes explicit Some(None) from a raw None
        return becoming Nothing. Relies on the isinstance(outcome, Option)
        check running before the None check in the implementation."""

        @wrap_option
        def f():
            return Some(None)

        result = f()
        assert result.is_some()
        assert result.unwrap() is None

    def test_wrap_option_exception_becomes_nothing(self):
        """A raised exception is caught and converted to Nothing, and the
        original exception is preserved for re-raise on unwrap(), mirroring
        wrap_result's exception-preservation guarantee."""

        @wrap_option
        def f():
            raise ValueError("bad input")

        result = f()
        assert result.is_nothing()
        with pytest.raises(ValueError, match="bad input"):
            result.unwrap()

    def test_wrap_option_preserves_function_name(self):
        """functools.wraps preserves __name__, matching wrap_result's convention."""

        @wrap_option
        def my_named_function():
            return 1

        assert my_named_function.__name__ == "my_named_function"

    def test_wrap_option_passes_args_and_kwargs(self):
        """Decorated function still receives its original arguments."""

        @wrap_option
        def add(a, b, *, c=0):
            return a + b + c

        result = add(1, 2, c=3)
        assert result.is_some()
        assert result.unwrap() == 6

    def test_wrap_option_base_exception_propagates(self):
        """A BaseException that isn't an Exception (e.g. KeyboardInterrupt)
        propagates rather than being converted to Nothing - only
        `except Exception` is caught, so control-flow signals and bugs
        aren't silently masked."""

        class _Signal(BaseException):
            pass

        @wrap_option
        def f():
            raise _Signal("interrupted")

        with pytest.raises(_Signal):
            f()
