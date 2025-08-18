"""
Tests for core utility functions in logerr.utils module.
"""

from logerr.utils import execute, log, nullable


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
        result = execute(lambda: "hello", on_exception="option")
        assert result.is_some()
        assert result.unwrap() == "hello"

    def test_execute_none_result_option(self):
        """Test execute when callable returns None for option mode."""
        result = execute(lambda: None, on_exception="option")
        assert result.is_nothing()

    def test_execute_exception_option(self):
        """Test execute with exception returning Option."""
        result = execute(lambda: 1 / 0, on_exception="option")
        assert result.is_nothing()


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
