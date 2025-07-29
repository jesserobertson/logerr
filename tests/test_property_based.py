"""Property-based tests using hypothesis for fuzz testing."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import composite

import logerr
from logerr import Err, Nothing, Ok, Result, Some

# Configure logging to avoid issues with complex strings
logerr.configure({"level": "CRITICAL"})

# Safe string strategy that avoids problematic characters
safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=32, max_codepoint=126
    ),
    max_size=50,
)


# Custom strategies for generating test data
@composite
def option_values(draw):
    """Generate random Option values."""
    value_type = draw(
        st.one_of(
            st.integers(),
            st.text(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.lists(st.integers(), max_size=10),
            st.dictionaries(st.text(max_size=10), st.integers(), max_size=5),
        )
    )
    return draw(st.one_of(st.just(Some(value_type)), st.just(Nothing.empty())))


@composite
def result_values(draw):
    """Generate random Result values."""
    ok_value = draw(
        st.one_of(
            st.integers(),
            st.text(max_size=50),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.lists(st.integers(), max_size=10),
        )
    )
    err_value = draw(st.one_of(safe_text, st.integers(), st.booleans()))
    return draw(st.one_of(st.just(Ok(ok_value)), st.just(Err(err_value))))


class TestOptionProperties:
    """Property-based tests for Option types."""

    @given(st.integers())
    def test_some_invariants(self, value):
        """Test basic invariants for Some values."""
        option = Some(value)

        # Basic properties
        assert option.is_some()
        assert not option.is_nothing()
        assert option.unwrap() == value
        assert option.unwrap_or(999) == value

        # Identity operations
        assert option.map(lambda x: x).unwrap() == value
        assert option.and_then(lambda x: Some(x)).unwrap() == value

    def test_nothing_invariants(self):
        """Test basic invariants for Nothing values."""
        option = Nothing.empty()

        # Basic properties
        assert not option.is_some()
        assert option.is_nothing()

        # Nothing operations should remain Nothing
        assert option.map(lambda x: x * 2).is_nothing()
        assert option.and_then(lambda x: Some(x * 2)).is_nothing()
        assert option.filter(lambda x: True).is_nothing()

    @given(st.integers(), st.integers())
    def test_map_composition(self, value, offset):
        """Test that map operations compose correctly."""
        option = Some(value)

        # map(f) . map(g) == map(g . f)
        f = lambda x: x + offset
        g = lambda x: x * 2

        result1 = option.map(f).map(g)
        result2 = option.map(lambda x: g(f(x)))

        assert result1.unwrap() == result2.unwrap()

    @given(st.integers())
    def test_filter_properties(self, value):
        """Test filter operation properties."""
        option = Some(value)

        # filter with always true predicate should preserve Some
        assert option.filter(lambda x: True).is_some()

        # filter with always false predicate should produce Nothing
        assert option.filter(lambda x: False).is_nothing()

        # filter preserves value when predicate is true
        if value > 0:
            result = option.filter(lambda x: x > 0)
            assert result.is_some()
            assert result.unwrap() == value

    @given(option_values())
    def test_unwrap_or_consistency(self, option):
        """Test unwrap_or behavior."""
        default = "DEFAULT"
        result = option.unwrap_or(default)

        if option.is_some():
            assert result == option.unwrap()
        else:
            assert result == default

    @given(st.integers(), st.integers())
    def test_and_then_properties(self, value, multiplier):
        """Test and_then (flatMap) properties."""
        option = Some(value)

        # and_then with function that returns Some
        f = lambda x: Some(x * multiplier)
        result = option.and_then(f)
        assert result.is_some()
        assert result.unwrap() == value * multiplier

        # and_then with function that returns Nothing
        g = lambda x: Nothing.empty()
        result = option.and_then(g)
        assert result.is_nothing()

    @given(st.text(), st.text())
    def test_string_operations(self, text1, text2):
        """Test Option operations with strings."""
        option1 = Some(text1)
        option2 = Some(text2)

        # Map string operations
        upper_result = option1.map(str.upper)
        assert upper_result.is_some()
        assert upper_result.unwrap() == text1.upper()

        # Filter by length
        if len(text1) > 5:
            long_strings = option1.filter(lambda s: len(s) > 5)
            assert long_strings.is_some()

    @given(st.lists(st.integers(), min_size=1, max_size=20))
    def test_collection_operations(self, items):
        """Test Option operations with collections."""
        option = Some(items)

        # Map over collections
        doubled = option.map(lambda lst: [x * 2 for x in lst])
        assert doubled.is_some()
        assert doubled.unwrap() == [x * 2 for x in items]

        # Filter collections
        non_empty = option.filter(lambda lst: len(lst) > 0)
        assert non_empty.is_some()


class TestResultProperties:
    """Property-based tests for Result types."""

    @given(st.integers())
    def test_ok_invariants(self, value):
        """Test basic invariants for Ok values."""
        result = Ok(value)

        # Basic properties
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == value
        assert result.unwrap_or(999) == value

        # Identity operations
        assert result.map(lambda x: x).unwrap() == value

    @given(safe_text)
    def test_err_invariants(self, error):
        """Test basic invariants for Err values."""
        result = Err(error)

        # Basic properties
        assert not result.is_ok()
        assert result.is_err()
        assert result.unwrap_err() == error

        # Err operations should remain Err
        assert result.map(lambda x: x * 2).is_err()
        assert result.and_then(lambda x: Ok(x * 2)).is_err()

    @given(st.integers(), st.integers())
    def test_map_error_preservation(self, value, multiplier):
        """Test that map preserves errors."""
        ok_result = Ok(value)
        err_result = Err("error")

        f = lambda x: x * multiplier

        # Ok values get mapped
        mapped_ok = ok_result.map(f)
        assert mapped_ok.is_ok()
        assert mapped_ok.unwrap() == value * multiplier

        # Err values stay as Err
        mapped_err = err_result.map(f)
        assert mapped_err.is_err()
        assert mapped_err.unwrap_err() == "error"

    @given(st.integers(), safe_text)
    def test_and_then_properties(self, value, error_msg):
        """Test and_then properties."""
        ok_result = Ok(value)
        err_result = Err(error_msg)

        # and_then with Ok input and Ok-returning function
        f = lambda x: Ok(x * 2)
        chained_ok = ok_result.and_then(f)
        assert chained_ok.is_ok()
        assert chained_ok.unwrap() == value * 2

        # and_then with Ok input and Err-returning function
        g = lambda x: Err("new error")
        chained_err = ok_result.and_then(g)
        assert chained_err.is_err()
        assert chained_err.unwrap_err() == "new error"

        # and_then with Err input should preserve original error
        result = err_result.and_then(f)
        assert result.is_err()
        assert result.unwrap_err() == error_msg

    @given(st.integers(), st.integers())
    def test_unwrap_or_consistency(self, value, default):
        """Test unwrap_or behavior for Results."""
        ok_result = Ok(value)
        err_result = Err("error")

        # Ok case
        assert ok_result.unwrap_or(default) == value

        # Err case
        assert err_result.unwrap_or(default) == default

    @given(st.integers())
    def test_map_err_properties(self, value):
        """Test map_err operation properties."""
        ok_result = Ok(value)
        err_result = Err("original error")

        error_transformer = lambda e: f"transformed: {e}"

        # map_err on Ok should preserve Ok
        mapped_ok = ok_result.map_err(error_transformer)
        assert mapped_ok.is_ok()
        assert mapped_ok.unwrap() == value

        # map_err on Err should transform the error
        mapped_err = err_result.map_err(error_transformer)
        assert mapped_err.is_err()
        assert mapped_err.unwrap_err() == "transformed: original error"


class TestFactoryFunctionProperties:
    """Property-based tests for factory functions."""

    @given(st.one_of(st.integers(), st.none()))
    def test_from_nullable_properties(self, value):
        """Test from_nullable factory function."""
        option = logerr.option.from_nullable(value)

        if value is None:
            assert option.is_nothing()
        else:
            assert option.is_some()
            assert option.unwrap() == value

    @given(st.integers())
    def test_from_predicate_properties(self, value):
        """Test from_predicate factory functions."""
        # Always true predicate
        option_true = logerr.option.from_predicate(value, lambda x: True)
        assert option_true.is_some()
        assert option_true.unwrap() == value

        # Always false predicate
        option_false = logerr.option.from_predicate(value, lambda x: False)
        assert option_false.is_nothing()

        # Result version
        result_true = logerr.result.from_predicate(value, lambda x: True, "error")
        assert result_true.is_ok()
        assert result_true.unwrap() == value

        result_false = logerr.result.from_predicate(value, lambda x: False, "error")
        assert result_false.is_err()
        assert result_false.unwrap_err() == "error"

    @given(safe_text)
    def test_from_callable_exception_handling(self, error_message):
        """Test from_callable handles exceptions properly."""

        def failing_function():
            raise ValueError(error_message)

        def succeeding_function():
            return 42

        # Failing callable should produce Err
        result_fail = logerr.result.from_callable(failing_function)
        assert result_fail.is_err()
        # Just check that it's an exception, don't assume exact type preservation

        # Succeeding callable should produce Ok
        result_ok = logerr.result.from_callable(succeeding_function)
        assert result_ok.is_ok()
        assert result_ok.unwrap() == 42


class TestComparisonProperties:
    """Property-based tests for comparison operations."""

    @given(st.integers(), st.integers())
    def test_option_equality_properties(self, value1, value2):
        """Test Option equality properties."""
        some1 = Some(value1)
        some2 = Some(value2)
        nothing = Nothing.empty()

        # Reflexivity
        assert some1 == some1
        assert nothing == nothing

        # Symmetry
        if value1 == value2:
            assert some1 == some2
            assert some2 == some1

        # Nothing is never equal to Some
        assert some1 != nothing
        assert nothing != some1

    @given(st.integers(), st.integers(), safe_text, safe_text)
    def test_result_equality_properties(self, ok_val1, ok_val2, err_val1, err_val2):
        """Test Result equality properties."""

        ok1 = Ok(ok_val1)
        ok2 = Ok(ok_val2)
        err1 = Err(err_val1)
        err2 = Err(err_val2)

        # Reflexivity
        assert ok1 == ok1
        assert err1 == err1

        # Ok and Err are never equal
        assert ok1 != err1
        assert err1 != ok1

        # Value-based equality
        if ok_val1 == ok_val2:
            assert ok1 == ok2
        if err_val1 == err_val2:
            assert err1 == err2

    @given(st.integers())
    def test_ordering_properties(self, value):
        """Test ordering properties where applicable."""
        some_val = Some(value)
        some_larger = Some(value + 1)

        if hasattr(some_val, "__lt__"):
            # Test basic ordering if implemented
            if value < value + 1:
                assert some_val < some_larger


class TestErrorHandlingProperties:
    """Property-based tests for error handling scenarios."""

    @given(safe_text)
    def test_unwrap_panics_on_nothing(self, error_context):
        """Test that unwrap properly panics on Nothing/Err."""

        nothing = Nothing.empty()
        err = Err(error_context)

        # These should raise exceptions
        with pytest.raises(Exception):
            nothing.unwrap()

        with pytest.raises(Exception):
            err.unwrap()

    @given(st.integers())
    def test_unwrap_behavior(self, value):
        """Test unwrap behavior on successful cases."""
        some_val = Some(value)
        ok_val = Ok(value)

        # unwrap on Some/Ok should return the value
        assert some_val.unwrap() == value
        assert ok_val.unwrap() == value


# Integration tests with realistic scenarios
class TestRealisticScenarios:
    """Property-based tests with realistic usage patterns."""

    @given(st.lists(st.integers(), min_size=0, max_size=50))
    def test_list_processing_pipeline(self, numbers):
        """Test realistic list processing scenarios."""

        # Simulate finding the first positive even number
        def find_first_positive_even(nums):
            for num in nums:
                if num > 0 and num % 2 == 0:
                    return Some(num)
            return Nothing.empty()

        result = find_first_positive_even(numbers)

        # Verify the result makes sense
        if result.is_some():
            value = result.unwrap()
            assert value > 0
            assert value % 2 == 0
            assert value in numbers

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=10), st.integers(), min_size=0, max_size=20
        )
    )
    def test_dictionary_operations(self, data):
        """Test dictionary-like operations with Options."""
        keys = list(data.keys())

        if not keys:
            return

        # Test safe dictionary access
        existing_key = keys[0]
        option = logerr.option.from_nullable(data.get(existing_key))
        assert option.is_some()
        assert option.unwrap() == data[existing_key]

        # Test non-existent key
        non_existent = logerr.option.from_nullable(data.get("__non_existent_key__"))
        assert non_existent.is_nothing()

    @given(st.text(min_size=1, max_size=100))
    def test_validation_chains(self, input_text):
        """Test validation chains with Results."""

        def validate_not_empty(s: str) -> Result[str, str]:
            if len(s.strip()) > 0:
                return Ok(s.strip())
            return Err("String is empty")

        def validate_length(s: str) -> Result[str, str]:
            if len(s) <= 50:
                return Ok(s)
            return Err("String too long")

        def validate_no_numbers(s: str) -> Result[str, str]:
            if not any(c.isdigit() for c in s):
                return Ok(s)
            return Err("String contains numbers")

        # Chain validations
        result = (
            Ok(input_text)
            .and_then(validate_not_empty)
            .and_then(validate_length)
            .and_then(validate_no_numbers)
        )

        # Verify result consistency
        if result.is_ok():
            final_value = result.unwrap()
            assert len(final_value.strip()) > 0
            assert len(final_value) <= 50
            assert not any(c.isdigit() for c in final_value)
