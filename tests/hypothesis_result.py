"""
Hypothesis-based property tests for Result types.
"""

from hypothesis import assume, given
from hypothesis import strategies as st

from logerr import Err, Ok
from logerr.result import from_optional, from_predicate, of


class TestResultProperties:
    """Property-based tests for Result behavior."""

    @given(st.integers())
    def test_ok_roundtrip_unwrap(self, value: int):
        """Test that Ok(value).unwrap() == value for any value."""
        result = Ok(value)
        assert result.unwrap() == value

    @given(st.text())
    def test_ok_is_ok_is_true(self, value: str):
        """Test that Ok(value).is_ok() is always True."""
        result = Ok(value)
        assert result.is_ok() is True
        assert result.is_err() is False

    @given(st.text())
    def test_err_is_err_is_true(self, error: str):
        """Test that Err(error).is_err() is always True."""
        result = Err(error, _skip_logging=True)
        assert result.is_err() is True
        assert result.is_ok() is False

    @given(st.integers(), st.integers())
    def test_unwrap_or_returns_value_for_ok(self, value: int, default: int):
        """Test that Ok(value).unwrap_or(default) == value."""
        result = Ok(value)
        assert result.unwrap_or(default) == value

    @given(st.text(), st.integers())
    def test_unwrap_or_returns_default_for_err(self, error: str, default: int):
        """Test that Err(error).unwrap_or(default) == default."""
        result = Err(error, _skip_logging=True)
        assert result.unwrap_or(default) == default

    @given(st.text(), st.integers())
    def test_unwrap_or_else_calls_function_for_err(self, error: str, default: int):
        """Test that Err.unwrap_or_else(f) calls f(error)."""
        result = Err(error, _skip_logging=True)
        call_count = 0

        def generate_default(err):
            nonlocal call_count
            call_count += 1
            assert err == error
            return default

        value = result.unwrap_or_else(generate_default)
        assert value == default
        assert call_count == 1

    @given(st.integers())
    def test_unwrap_or_else_does_not_call_function_for_ok(self, value: int):
        """Test that Ok.unwrap_or_else(f) doesn't call f()."""
        result = Ok(value)
        call_count = 0

        def should_not_be_called(err):
            nonlocal call_count
            call_count += 1
            return 999

        actual_value = result.unwrap_or_else(should_not_be_called)
        assert actual_value == value
        assert call_count == 0


class TestResultTransforms:
    """Property-based tests for Result transformations."""

    @given(st.integers())
    def test_map_preserves_ok_structure(self, value: int):
        """Test that mapping preserves Ok structure."""
        result = Ok(value)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_ok()
        assert mapped.unwrap() == value * 2

    @given(st.text())
    def test_map_preserves_err_structure(self, error: str):
        """Test that mapping Err always returns Err."""
        result = Err(error, _skip_logging=True)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_err()

    @given(st.integers())
    def test_then_chains_ok_operations(self, value: int):
        """Test that then() properly chains Ok operations."""
        result = Ok(value)
        chained = result.then(lambda x: Ok(x * 2))
        assert chained.is_ok()
        assert chained.unwrap() == value * 2

    @given(st.text())
    def test_then_short_circuits_on_err(self, error: str):
        """Test that then() short-circuits on Err."""
        result = Err(error, _skip_logging=True)
        call_count = 0

        def should_not_be_called(x):
            nonlocal call_count
            call_count += 1
            return Ok(x * 2)

        chained = result.then(should_not_be_called)
        assert chained.is_err()
        assert call_count == 0

    @given(st.text(), st.integers())
    def test_map_err_transforms_error(self, error: str, multiplier: int):
        """Test that map_err transforms the error value."""
        result = Err(error, _skip_logging=True)
        mapped = result.map_err(lambda e: f"{e}_{multiplier}")
        assert mapped.is_err()
        assert mapped.unwrap_err() == f"{error}_{multiplier}"

    @given(st.integers())
    def test_map_err_preserves_ok(self, value: int):
        """Test that map_err doesn't affect Ok values."""
        result = Ok(value)
        mapped = result.map_err(lambda e: f"transformed_{e}")
        assert mapped.is_ok()
        assert mapped.unwrap() == value


class TestResultFactories:
    """Property-based tests for Result factory functions."""

    @given(st.integers())
    def test_result_of_successful_callable(self, value: int):
        """Test Result.of with successful callables."""
        result = of(lambda: value)
        assert result.is_ok()
        assert result.unwrap() == value

    def test_result_of_failing_callable(self):
        """Test Result.of with failing callable."""
        result = of(lambda: 1 / 0)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ZeroDivisionError)

    @given(st.integers(), st.text())
    def test_from_optional_with_values(self, value: int, error: str):
        """Test from_optional with non-None values."""
        result = from_optional(value, error)
        assert result.is_ok()
        assert result.unwrap() == value

    @given(st.text())
    def test_from_optional_with_none(self, error: str):
        """Test from_optional with None."""
        result = from_optional(None, error)
        assert result.is_err()
        assert result.unwrap_err() == error

    @given(st.integers(), st.text())
    def test_from_predicate_passing(self, value: int, error: str):
        """Test from_predicate when predicate passes."""
        assume(value > 0)
        result = from_predicate(value, lambda x: x > 0, error)
        assert result.is_ok()
        assert result.unwrap() == value

    @given(st.integers(), st.text())
    def test_from_predicate_failing(self, value: int, error: str):
        """Test from_predicate when predicate fails."""
        assume(value <= 0)
        result = from_predicate(value, lambda x: x > 0, error)
        assert result.is_err()
        assert result.unwrap_err() == error


class TestResultComparisons:
    """Property-based tests for Result comparisons."""

    @given(st.integers())
    def test_ok_equality_reflexive(self, value: int):
        """Test that Ok(x) == Ok(x)."""
        result1 = Ok(value)
        result2 = Ok(value)
        assert result1 == result2

    @given(st.integers(), st.integers())
    def test_ok_equality_different_values(self, value1: int, value2: int):
        """Test Ok equality with different values."""
        assume(value1 != value2)
        result1 = Ok(value1)
        result2 = Ok(value2)
        assert result1 != result2

    @given(st.text())
    def test_err_equality_reflexive(self, error: str):
        """Test that Err(x) == Err(x)."""
        result1 = Err(error, _skip_logging=True)
        result2 = Err(error, _skip_logging=True)
        assert result1 == result2

    @given(st.integers(), st.text())
    def test_ok_not_equal_to_err(self, value: int, error: str):
        """Test that Ok is never equal to Err."""
        ok_result = Ok(value)
        err_result = Err(error, _skip_logging=True)
        assert ok_result != err_result
        assert err_result != ok_result
