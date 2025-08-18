"""
Hypothesis-based property tests for Option types.
"""

from hypothesis import assume, given
from hypothesis import strategies as st

from logerr import Nothing, Option, Some
from logerr.option import from_nullable, from_predicate


class TestOptionProperties:
    """Property-based tests for Option behavior."""

    @given(st.integers())
    def test_some_roundtrip_unwrap(self, value: int):
        """Test that Some(value).unwrap() == value for any value."""
        option = Some(value)
        assert option.unwrap() == value

    @given(st.text())
    def test_some_is_some_is_true(self, value: str):
        """Test that Some(value).is_some() is always True."""
        option = Some(value)
        assert option.is_some() is True
        assert option.is_nothing() is False

    @given(st.integers(), st.integers())
    def test_unwrap_or_returns_value_for_some(self, value: int, default: int):
        """Test that Some(value).unwrap_or(default) == value."""
        option = Some(value)
        assert option.unwrap_or(default) == value

    @given(st.integers())
    def test_unwrap_or_returns_default_for_nothing(self, default: int):
        """Test that Nothing.unwrap_or(default) == default."""
        nothing = Nothing.empty()
        assert nothing.unwrap_or(default) == default

    @given(st.integers())
    def test_unwrap_or_else_calls_function_for_nothing(self, default: int):
        """Test that Nothing.unwrap_or_else(f) calls f()."""
        nothing = Nothing.empty()
        call_count = 0

        def generate_default():
            nonlocal call_count
            call_count += 1
            return default

        result = nothing.unwrap_or_else(generate_default)
        assert result == default
        assert call_count == 1

    @given(st.integers())
    def test_unwrap_or_else_does_not_call_function_for_some(self, value: int):
        """Test that Some.unwrap_or_else(f) doesn't call f()."""
        option = Some(value)
        call_count = 0

        def should_not_be_called():
            nonlocal call_count
            call_count += 1
            return 999

        result = option.unwrap_or_else(should_not_be_called)
        assert result == value
        assert call_count == 0


class TestOptionTransforms:
    """Property-based tests for Option transformations."""

    @given(st.integers())
    def test_map_preserves_some_structure(self, value: int):
        """Test that mapping preserves Some structure."""
        option = Some(value)
        mapped = option.map(lambda x: x * 2)
        assert mapped.is_some()
        assert mapped.unwrap() == value * 2

    @given(st.text())
    def test_map_preserves_nothing_structure(self, _):
        """Test that mapping Nothing always returns Nothing."""
        nothing = Nothing.empty()
        mapped = nothing.map(lambda x: x.upper())
        assert mapped.is_nothing()

    @given(st.integers())
    def test_then_chains_some_operations(self, value: int):
        """Test that then() properly chains Some operations."""
        assume(value != 0)  # Avoid division by zero

        option = Some(value)
        result = option.then(lambda x: Some(x * 2))
        assert result.is_some()
        assert result.unwrap() == value * 2

    @given(st.integers())
    def test_then_short_circuits_on_nothing(self, _):
        """Test that then() short-circuits on Nothing."""
        nothing = Nothing.empty()
        call_count = 0

        def should_not_be_called(x):
            nonlocal call_count
            call_count += 1
            return Some(x * 2)

        result = nothing.then(should_not_be_called)
        assert result.is_nothing()
        assert call_count == 0


class TestOptionFactories:
    """Property-based tests for Option factory functions."""

    @given(st.integers())
    def test_from_nullable_with_values(self, value: int):
        """Test from_nullable with non-None values."""
        option = from_nullable(value)
        assert option.is_some()
        assert option.unwrap() == value

    def test_from_nullable_with_none(self):
        """Test from_nullable with None."""
        option = from_nullable(None)
        assert option.is_nothing()

    @given(st.integers())
    def test_from_predicate_passing(self, value: int):
        """Test from_predicate when predicate passes."""
        assume(value > 0)
        option = from_predicate(value, lambda x: x > 0)
        assert option.is_some()
        assert option.unwrap() == value

    @given(st.integers())
    def test_from_predicate_failing(self, value: int):
        """Test from_predicate when predicate fails."""
        assume(value <= 0)
        option = from_predicate(value, lambda x: x > 0)
        assert option.is_nothing()

    @given(st.integers())
    def test_option_of_successful_callable(self, value: int):
        """Test Option.of with successful callables."""
        option = Option.of(lambda: value)
        assert option.is_some()
        assert option.unwrap() == value

    def test_option_of_none_returning_callable(self):
        """Test Option.of with None-returning callable."""
        option = Option.of(lambda: None)
        assert option.is_nothing()


class TestOptionComparisons:
    """Property-based tests for Option comparisons."""

    @given(st.integers())
    def test_some_equality_reflexive(self, value: int):
        """Test that Some(x) == Some(x)."""
        option1 = Some(value)
        option2 = Some(value)
        assert option1 == option2

    @given(st.integers(), st.integers())
    def test_some_equality_different_values(self, value1: int, value2: int):
        """Test Some equality with different values."""
        assume(value1 != value2)
        option1 = Some(value1)
        option2 = Some(value2)
        assert option1 != option2

    def test_nothing_equality_reflexive(self):
        """Test that Nothing instances are equal."""
        nothing1 = Nothing.empty()
        nothing2 = Nothing.empty()
        assert nothing1 == nothing2

    @given(st.integers())
    def test_some_not_equal_to_nothing(self, value: int):
        """Test that Some is never equal to Nothing."""
        some_option = Some(value)
        nothing = Nothing.empty()
        assert some_option != nothing
        assert nothing != some_option
