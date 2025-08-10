"""
Tests for advanced utility functions in logerr.recipes.utilities module.
"""

import pytest

from logerr import Nothing, Some
from logerr.recipes.utilities import (
    attribute,
    chain,
    error,
    pipe,
    resolve,
    try_chain,
    validate,
)


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
        assert result == "HELLO"

    def test_pipe_multiple_functions(self):
        """Test pipe with multiple functions."""
        result = pipe("  hello world  ", str.strip, str.upper, lambda s: s.split())
        assert result == ["HELLO", "WORLD"]

    def test_pipe_no_functions(self):
        """Test pipe with no functions."""
        result = pipe("hello")
        assert result == "hello"


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
