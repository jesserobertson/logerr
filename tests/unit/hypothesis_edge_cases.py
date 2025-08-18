"""
Hypothesis-based edge case tests for robustness and error handling.
"""

import sys

from hypothesis import given, settings
from hypothesis import strategies as st

from logerr import Err, Nothing, Ok, Result, Some


class TestEdgeCases:
    """Property-based tests for edge cases and error conditions."""

    @given(st.text())
    def test_option_handles_large_strings(self, large_text: str):
        """Test Option handles arbitrarily large strings."""
        option = Some(large_text)
        assert option.unwrap() == large_text
        assert option.is_some()

    @given(st.integers(min_value=-sys.maxsize, max_value=sys.maxsize))
    def test_option_handles_extreme_integers(self, extreme_int: int):
        """Test Option handles extreme integer values."""
        option = Some(extreme_int)
        assert option.unwrap() == extreme_int

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_option_handles_float_values(self, float_val: float):
        """Test Option handles various float values."""
        option = Some(float_val)
        # Use approximate equality for floats
        unwrapped = option.unwrap()
        assert abs(unwrapped - float_val) < 1e-10 or unwrapped == float_val

    @given(st.lists(st.integers(), min_size=0, max_size=100))
    def test_option_handles_collections(self, int_list: list):
        """Test Option works with collections."""
        option = Some(int_list)
        assert option.unwrap() == int_list
        assert len(option.unwrap()) == len(int_list)

    @given(st.dictionaries(st.text(), st.integers(), min_size=0, max_size=50))
    def test_option_handles_dictionaries(self, dictionary: dict):
        """Test Option works with dictionaries."""
        option = Some(dictionary)
        assert option.unwrap() == dictionary

    def test_option_handles_none_explicitly(self):
        """Test Option explicitly handles None values."""
        # Some should not accept None in normal usage
        option = Nothing.from_none("Explicit None handling")
        assert option.is_nothing()

    @given(st.text())
    def test_nothing_reason_preserved(self, reason: str):
        """Test that Nothing preserves the reason string."""
        nothing = Nothing(reason, _skip_logging=True)
        assert nothing.is_nothing()
        # Reason is preserved in repr
        assert reason in repr(nothing)

    @settings(max_examples=50)  # Reduce examples for exception tests
    @given(st.text())
    def test_result_exception_handling(self, error_msg: str):
        """Test Result handles various exception types."""

        def raise_error():
            raise ValueError(error_msg)

        result = Result.of(raise_error)
        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, ValueError)
        assert str(error) == error_msg

    @given(st.text())
    def test_map_error_propagation(self, error_text: str):
        """Test that map operations properly propagate errors."""

        def failing_transform(x):
            raise RuntimeError(error_text)

        # Option case
        option = Some(42)
        mapped_option = option.map(failing_transform)
        assert mapped_option.is_nothing()

        # Result case
        result = Ok(42)
        mapped_result = result.map(failing_transform)
        assert mapped_result.is_err()
        assert isinstance(mapped_result.unwrap_err(), RuntimeError)

    @given(st.text())
    def test_then_error_propagation(self, error_text: str):
        """Test that then operations properly propagate errors."""

        def failing_chain(x):
            raise RuntimeError(error_text)

        # Option case
        option = Some(42)
        chained_option = option.then(failing_chain)
        assert chained_option.is_nothing()

        # Result case
        result = Ok(42)
        chained_result = result.then(failing_chain)
        assert chained_result.is_err()


class TestMonadicLaws:
    """Property-based tests for monadic laws that Option and Result should follow."""

    @given(st.integers())
    def test_option_left_identity(self, value: int):
        """Test Option left identity: Some(a).then(f) == f(a)."""

        def double_if_positive(x):
            return Some(x * 2) if x > 0 else Nothing.empty()

        left_side = Some(value).then(double_if_positive)
        right_side = double_if_positive(value)

        assert left_side == right_side

    @given(st.integers())
    def test_option_right_identity(self, value: int):
        """Test Option right identity: m.then(Some) == m."""
        option = Some(value)
        chained = option.then(lambda x: Some(x))
        assert chained == option

    @given(st.integers())
    def test_result_left_identity(self, value: int):
        """Test Result left identity: Ok(a).then(f) == f(a)."""

        def double_if_positive(x):
            return Ok(x * 2) if x > 0 else Err("negative", _skip_logging=True)

        left_side = Ok(value).then(double_if_positive)
        right_side = double_if_positive(value)

        assert left_side == right_side

    @given(st.integers())
    def test_result_right_identity(self, value: int):
        """Test Result right identity: m.then(Ok) == m."""
        result = Ok(value)
        chained = result.then(lambda x: Ok(x))
        assert chained == result

    @given(st.integers())
    def test_option_associativity(self, value: int):
        """Test Option associativity: m.then(f).then(g) == m.then(lambda x: f(x).then(g))."""

        def f(x):
            return Some(x + 1) if x >= 0 else Nothing.empty()

        def g(x):
            return Some(x * 2) if x % 2 == 0 else Nothing.empty()

        option = Some(value)
        left = option.then(f).then(g)
        right = option.then(lambda x: f(x).then(g))

        assert left == right


class TestComparisonProperties:
    """Property-based tests for comparison operations."""

    @given(st.integers())
    def test_option_ordering_some_vs_nothing(self, value: int):
        """Test that Some is always greater than Nothing."""
        some_option = Some(value)
        nothing = Nothing.empty()

        assert some_option > nothing
        assert nothing < some_option
        assert some_option >= nothing
        assert nothing <= some_option

    @given(st.integers())
    def test_result_ordering_ok_vs_err(self, value: int):
        """Test that Ok is always greater than Err."""
        ok_result = Ok(value)
        err_result = Err("error", _skip_logging=True)

        assert ok_result > err_result
        assert err_result < ok_result
        assert ok_result >= err_result
        assert err_result <= ok_result
