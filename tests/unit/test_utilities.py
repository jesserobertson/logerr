"""
Tests for core utility functions in logerr.utilities module.
"""

import pytest

from logerr.utilities import execute, log, nullable

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
