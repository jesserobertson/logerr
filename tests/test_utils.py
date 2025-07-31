"""
Tests for utility functions in logerr.utils module.
"""

import pytest

from logerr.utils import (
    attribute,
    error,
    execute,
    nullable,
    resolve,
    validate,
)


class TestExecute:
    """Test execute utility function."""

    def test_successful_execution_returns_ok(self):
        """Test that successful execution returns Ok result."""
        result = execute(lambda: 42)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_exception_returns_err(self):
        """Test that exceptions return Err result."""
        result = execute(lambda: 1 / 0)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ZeroDivisionError)

    def test_option_mode_successful(self):
        """Test execute with option mode for successful execution."""
        result = execute(lambda: "value", on_exception="option")
        assert result.is_some()
        assert result.unwrap() == "value"

    def test_option_mode_exception(self):
        """Test execute with option mode for exceptions."""
        result = execute(lambda: 1 / 0, on_exception="option")
        assert result.is_nothing()


class TestNullable:
    """Test nullable utility function."""

    def test_non_null_value_returns_some(self):
        """Test that non-null values return Some."""
        result = nullable("value")
        assert result.is_some()
        assert result.unwrap() == "value"

    def test_null_value_returns_nothing(self):
        """Test that null values return Nothing."""
        result = nullable(None)
        assert result.is_nothing()

    def test_result_mode_non_null(self):
        """Test nullable in result mode with non-null value."""
        result = nullable("value", return_type="result")
        assert result.is_ok()
        assert result.unwrap() == "value"

    def test_result_mode_null_with_error_factory(self):
        """Test nullable in result mode with null and error factory."""
        result = nullable(
            None, return_type="result", error_factory=lambda: ValueError("Custom error")
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)
        assert str(result.unwrap_err()) == "Custom error"


class TestValidate:
    """Test validate utility function."""

    def test_passing_predicate_returns_ok(self):
        """Test that passing predicate returns Ok."""
        result = validate(
            5, lambda x: x > 0, error_factory=ValueError("Must be positive")
        )
        assert result.is_ok()
        assert result.unwrap() == 5

    def test_failing_predicate_returns_err(self):
        """Test that failing predicate returns Err."""
        result = validate(
            -1, lambda x: x > 0, error_factory=ValueError("Must be positive")
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)
        assert str(result.unwrap_err()) == "Must be positive"

    def test_predicate_exception_captured(self):
        """Test that exceptions in predicate are captured."""
        result = validate(
            "not_a_number",
            lambda x: int(x) > 0,  # This will raise ValueError
            error_factory=ValueError("Must be positive number"),
            capture_exceptions=True,
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)  # The exception from int()


class TestResolveDefaults:
    """Test resolve utility function."""

    def test_provided_value_used(self):
        """Test that provided value is used when not None."""
        result = resolve(10, 42)
        assert result == 10

    def test_default_value_used(self):
        """Test that default value is used when provided is None."""
        result = resolve(None, 42)
        assert result == 42

    def test_validator_passes(self):
        """Test that validator passes with valid value."""
        result = resolve(10, 42, validator=lambda x: x > 0)
        assert result == 10

    def test_validator_fails(self):
        """Test that validator raises ValueError when validation fails."""
        with pytest.raises(ValueError, match="failed validation"):
            resolve(-5, 42, validator=lambda x: x > 0)


class TestAttribute:
    """Test attribute utility function."""

    def test_existing_attribute(self):
        """Test getting existing attribute."""
        result = attribute(len, "__name__")
        assert result == "len"

    def test_missing_attribute_uses_default(self):
        """Test that missing attribute uses default value."""
        result = attribute(42, "__name__", "unknown")
        assert result == "unknown"

    def test_custom_default(self):
        """Test using custom default value."""
        result = attribute({}, "__name__", "custom_default")
        assert result == "custom_default"


class TestError:
    """Test error utility function."""

    def test_error_with_valid_options(self):
        """Test creating error with valid options."""
        err = error("INVALID", "log level", {"DEBUG", "INFO", "ERROR"})
        assert isinstance(err, ValueError)
        assert "Invalid log level 'INVALID'" in str(err)
        assert "Must be one of:" in str(err)

    def test_error_without_valid_options(self):
        """Test creating error without valid options."""
        err = error("bad_value", "parameter")
        assert isinstance(err, ValueError)
        assert "Invalid parameter: 'bad_value'" in str(err)
