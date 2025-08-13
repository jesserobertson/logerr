"""Tests for enhanced predicate functionality."""

import logerr
from logerr import Ok, Some


class TestOptionPredicateEnhancements:
    """Test enhanced predicate functionality for Option types."""

    def test_from_predicate_with_custom_error_message(self):
        """Test from_predicate with custom error message."""
        # Test successful predicate
        option = logerr.option.from_predicate(42, lambda x: x > 30)
        assert option.is_some()
        assert option.unwrap() == 42

        # Test failed predicate with custom message
        option = logerr.option.from_predicate(
            5, lambda x: x > 30, error_message="Number too small"
        )
        assert option.is_nothing()
        # We can't easily test the logged message content, but we can ensure it doesn't crash

    def test_from_predicate_backwards_compatibility(self):
        """Test that the enhanced from_predicate is backwards compatible."""
        # Old API without error_message should still work
        option = logerr.option.from_predicate(42, lambda x: x > 30)
        assert option.is_some()

        option = logerr.option.from_predicate(5, lambda x: x > 30)
        assert option.is_nothing()

    def test_predicate_filter_factory(self):
        """Test the new predicate_filter factory function."""
        # Create a reusable validator
        is_positive = logerr.option.predicate_filter(lambda x: x > 0)

        # Test with positive number
        result = is_positive(42)
        assert result.is_some()
        assert result.unwrap() == 42

        # Test with negative number
        result = is_positive(-5)
        assert result.is_nothing()

    def test_predicate_filter_with_custom_message(self):
        """Test predicate_filter with custom error message."""
        email_validator = logerr.option.predicate_filter(
            lambda s: "@" in s, error_message="Invalid email format"
        )

        # Valid email
        result = email_validator("user@example.com")
        assert result.is_some()
        assert result.unwrap() == "user@example.com"

        # Invalid email
        result = email_validator("invalid-email")
        assert result.is_nothing()

    def test_predicate_filter_chaining(self):
        """Test using predicate_filter with method chaining."""
        is_long_string = logerr.option.predicate_filter(lambda s: len(s) > 3)

        result = Some("hello").then(is_long_string).map(str.upper)

        assert result.is_some()
        assert result.unwrap() == "HELLO"

        # Test with short string that fails the filter
        result = Some("hi").then(is_long_string).map(str.upper)

        assert result.is_nothing()


class TestResultPredicateEnhancements:
    """Test enhanced predicate functionality for Result types."""

    def test_from_predicate_basic(self):
        """Test basic from_predicate functionality for Results."""
        # Test successful predicate
        result = logerr.result.from_predicate(42, lambda x: x > 30, "too small")
        assert result.is_ok()
        assert result.unwrap() == 42

        # Test failed predicate
        result = logerr.result.from_predicate(5, lambda x: x > 30, "too small")
        assert result.is_err()
        assert result.unwrap_or(0) == 0

        # Check error value
        error = result.unwrap_err()
        assert error == "too small"

    def test_from_predicate_with_exception(self):
        """Test from_predicate when predicate raises exception."""
        result = logerr.result.from_predicate(
            "not a number", lambda s: int(s) > 0, "conversion error"
        )
        assert result.is_err()
        # The error should be the caught exception, not our custom error
        # because the exception occurred during predicate evaluation

    def test_predicate_validator_factory(self):
        """Test the new predicate_validator factory function."""
        # Create a reusable validator
        validate_positive = logerr.result.predicate_validator(
            lambda x: x > 0, "must be positive"
        )

        # Test with positive number
        result = validate_positive(42)
        assert result.is_ok()
        assert result.unwrap() == 42

        # Test with negative number
        result = validate_positive(-5)
        assert result.is_err()
        assert result.unwrap_err() == "must be positive"

    def test_predicate_validator_chaining(self):
        """Test using predicate_validator with method chaining."""
        validate_even = logerr.result.predicate_validator(
            lambda x: x % 2 == 0, "must be even"
        )
        validate_positive = logerr.result.predicate_validator(
            lambda x: x > 0, "must be positive"
        )

        # Test successful chain
        result = Ok(42).then(validate_positive).then(validate_even).map(lambda x: x * 2)

        assert result.is_ok()
        assert result.unwrap() == 84

        # Test chain that fails at second validator
        result = (
            Ok(3)  # positive but odd
            .then(validate_positive)
            .then(validate_even)
            .map(lambda x: x * 2)
        )

        assert result.is_err()
        assert result.unwrap_err() == "must be even"

    def test_mixed_error_types(self):
        """Test predicate functions with different error types."""
        # String error
        validate_string = logerr.result.predicate_validator(
            lambda x: x > 0, "negative number"
        )
        result = validate_string(-5)
        assert result.is_err()
        assert result.unwrap_err() == "negative number"

        # Integer error code
        validate_int = logerr.result.predicate_validator(lambda x: x > 0, 400)
        result = validate_int(-5)
        assert result.is_err()
        assert result.unwrap_err() == 400

        # Custom error object
        class ValidationError:
            def __init__(self, message: str):
                self.message = message

            def __eq__(self, other):
                return (
                    isinstance(other, ValidationError) and self.message == other.message
                )

        validate_custom = logerr.result.predicate_validator(
            lambda x: x > 0, ValidationError("Value must be positive")
        )
        result = validate_custom(-5)
        assert result.is_err()
        assert result.unwrap_err().message == "Value must be positive"


class TestApiConsistency:
    """Test that the new predicate APIs are consistent and well-integrated."""

    def test_option_and_result_predicate_consistency(self):
        """Test that Option and Result predicate functions behave consistently."""

        def predicate(x):
            return x > 0

        value = 42
        negative_value = -5

        # Both should succeed with positive values
        option = logerr.option.from_predicate(value, predicate)
        result = logerr.result.from_predicate(value, predicate, "error")

        assert option.is_some()
        assert result.is_ok()
        assert option.unwrap() == result.unwrap() == value

        # Both should fail with negative values
        option = logerr.option.from_predicate(negative_value, predicate)
        result = logerr.result.from_predicate(negative_value, predicate, "error")

        assert option.is_nothing()
        assert result.is_err()

    def test_predicate_functions_are_accessible(self):
        """Test that all new predicate functions are accessible through the API."""
        # Option functions
        assert hasattr(logerr.option, "from_predicate")
        assert hasattr(logerr.option, "predicate_filter")

        # Result functions
        assert hasattr(logerr.result, "from_predicate")
        assert hasattr(logerr.result, "predicate_validator")

        # Ensure they're callable
        assert callable(logerr.option.from_predicate)
        assert callable(logerr.option.predicate_filter)
        assert callable(logerr.result.from_predicate)
        assert callable(logerr.result.predicate_validator)
