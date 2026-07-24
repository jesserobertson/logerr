"""
Hypothesis-based property tests for logerr.functools combinators.
"""

from hypothesis import given
from hypothesis import strategies as st

from logerr import Err, Nothing, Ok, Option, Result, Some
from logerr.functools import (
    and_option,
    and_result,
    err,
    flatten_option,
    flatten_result,
    ok,
    or_option,
    or_result,
    zip_option,
    zip_result,
)


def _option_strategy(inner: st.SearchStrategy[int]) -> st.SearchStrategy[Option[int]]:
    return st.one_of(inner.map(Some), st.just(Nothing.empty()))


def _result_strategy(
    ok_inner: st.SearchStrategy[int], err_inner: st.SearchStrategy[str]
) -> st.SearchStrategy[Result[int, str]]:
    return st.one_of(
        ok_inner.map(Ok), err_inner.map(lambda e: Err(e, _skip_logging=True))
    )


class TestZipOptionProperties:
    """Property-based tests for zip_option."""

    @given(_option_strategy(st.integers()), _option_strategy(st.integers()))
    def test_is_some_iff_both_some(self, a: Option[int], b: Option[int]):
        """zip_option(a, b) is Some iff both a and b are Some."""
        assert zip_option(a, b).is_some() == (a.is_some() and b.is_some())

    @given(st.integers(), st.integers())
    def test_some_pair_unwraps_to_tuple(self, x: int, y: int):
        """zip_option(Some(x), Some(y)).unwrap() == (x, y)."""
        assert zip_option(Some(x), Some(y)).unwrap() == (x, y)


class TestZipResultProperties:
    """Property-based tests for zip_result."""

    @given(
        _result_strategy(st.integers(), st.text()),
        _result_strategy(st.integers(), st.text()),
    )
    def test_is_ok_iff_both_ok(self, a: Result[int, str], b: Result[int, str]):
        """zip_result(a, b) is Ok iff both a and b are Ok."""
        assert zip_result(a, b).is_ok() == (a.is_ok() and b.is_ok())

    @given(st.integers(), st.integers())
    def test_ok_pair_unwraps_to_tuple(self, x: int, y: int):
        """zip_result(Ok(x), Ok(y)).unwrap() == (x, y)."""
        assert zip_result(Ok(x), Ok(y)).unwrap() == (x, y)


class TestFlattenProperties:
    """Property-based tests for flatten_option and flatten_result."""

    @given(st.integers())
    def test_flatten_option_some_of_some(self, x: int):
        """flatten_option(Some(Some(x))).unwrap() == x."""
        assert flatten_option(Some(Some(x))).unwrap() == x

    @given(st.integers())
    def test_flatten_result_ok_of_ok(self, x: int):
        """flatten_result(Ok(Ok(x))).unwrap() == x."""
        assert flatten_result(Ok(Ok(x))).unwrap() == x

    def test_flatten_option_nothing_is_nothing(self):
        """flatten_option(Nothing.empty()) is always Nothing."""
        assert flatten_option(Nothing.empty()).is_nothing()


class TestAndOrProperties:
    """Property-based tests for and_option/and_result/or_option/or_result."""

    @given(_option_strategy(st.integers()), _option_strategy(st.integers()))
    def test_and_option(self, a: Option[int], b: Option[int]):
        """and_option(a, b) is b when a is Some, otherwise Nothing."""
        result = and_option(a, b)
        if a.is_some():
            assert result == b
        else:
            assert result.is_nothing()

    @given(_option_strategy(st.integers()), _option_strategy(st.integers()))
    def test_or_option(self, a: Option[int], b: Option[int]):
        """or_option(a, b) is a when a is Some, otherwise b."""
        result = or_option(a, b)
        if a.is_some():
            assert result == a
        else:
            assert result == b

    @given(
        _result_strategy(st.integers(), st.text()),
        _result_strategy(st.integers(), st.text()),
    )
    def test_and_result(self, a: Result[int, str], b: Result[int, str]):
        """and_result(a, b) is b when a is Ok, otherwise an Err."""
        result = and_result(a, b)
        if a.is_ok():
            assert result == b
        else:
            assert result.is_err()

    @given(
        _result_strategy(st.integers(), st.text()),
        _result_strategy(st.integers(), st.text()),
    )
    def test_or_result(self, a: Result[int, str], b: Result[int, str]):
        """or_result(a, b) is a when a is Ok, otherwise b."""
        result = or_result(a, b)
        if a.is_ok():
            assert result == a
        else:
            assert result == b


class TestOkErrProperties:
    """Property-based tests for ok() and err()."""

    @given(_result_strategy(st.integers(), st.text()))
    def test_ok_extracts_value_when_ok(self, r: Result[int, str]):
        """ok(r).is_some() == r.is_ok(), unwrapping to the same value when Ok."""
        option = ok(r)
        assert option.is_some() == r.is_ok()
        if r.is_ok():
            assert option.unwrap() == r.unwrap()

    @given(_result_strategy(st.integers(), st.text()))
    def test_err_extracts_error_when_err(self, r: Result[int, str]):
        """err(r).is_some() == r.is_err(), unwrapping to the same error when Err."""
        option = err(r)
        assert option.is_some() == r.is_err()
        if r.is_err():
            assert option.unwrap() == r.unwrap_err()
