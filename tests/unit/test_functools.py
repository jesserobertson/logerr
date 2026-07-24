"""
Tests for logerr.functools module.
"""

import pytest

from logerr import Err, Nothing, Ok, Some
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

pytestmark = pytest.mark.unit


class TestZipOption:
    def test_both_some(self):
        result = zip_option(Some(1), Some("a"))
        assert result.is_some()
        assert result.unwrap() == (1, "a")

    def test_first_nothing(self):
        result = zip_option(Nothing.empty(), Some("a"))
        assert result.is_nothing()

    def test_second_nothing(self):
        result = zip_option(Some(1), Nothing.empty())
        assert result.is_nothing()

    def test_both_nothing(self):
        result = zip_option(Nothing.empty(), Nothing.empty())
        assert result.is_nothing()


class TestZipResult:
    def test_both_ok(self):
        result = zip_result(Ok(1), Ok("a"))
        assert result.is_ok()
        assert result.unwrap() == (1, "a")

    def test_first_err(self):
        result = zip_result(Err("boom"), Ok("a"))
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_second_err(self):
        result = zip_result(Ok(1), Err("boom"))
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_both_err_first_wins(self):
        result = zip_result(Err("first"), Err("second"))
        assert result.is_err()
        assert result.unwrap_err() == "first"


class TestFlattenOption:
    def test_some_of_some(self):
        result = flatten_option(Some(Some(42)))
        assert result.is_some()
        assert result.unwrap() == 42

    def test_some_of_nothing(self):
        result = flatten_option(Some(Nothing.empty()))
        assert result.is_nothing()

    def test_nothing(self):
        result = flatten_option(Nothing.empty())
        assert result.is_nothing()


class TestFlattenResult:
    def test_ok_of_ok(self):
        result = flatten_result(Ok(Ok(42)))
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_ok_of_err(self):
        result = flatten_result(Ok(Err("inner boom")))
        assert result.is_err()
        assert result.unwrap_err() == "inner boom"

    def test_outer_err(self):
        result = flatten_result(Err("outer boom"))
        assert result.is_err()
        assert result.unwrap_err() == "outer boom"


class TestAndOption:
    def test_some_returns_other(self):
        result = and_option(Some(1), Some("a"))
        assert result.is_some()
        assert result.unwrap() == "a"

    def test_some_other_nothing(self):
        result = and_option(Some(1), Nothing.empty())
        assert result.is_nothing()

    def test_nothing_short_circuits(self):
        result = and_option(Nothing.empty(), Some("a"))
        assert result.is_nothing()


class TestAndResult:
    def test_ok_returns_other(self):
        result = and_result(Ok(1), Ok("a"))
        assert result.is_ok()
        assert result.unwrap() == "a"

    def test_ok_other_err(self):
        result = and_result(Ok(1), Err("boom"))
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_err_short_circuits(self):
        result = and_result(Err("boom"), Ok("a"))
        assert result.is_err()
        assert result.unwrap_err() == "boom"


class TestOrOption:
    def test_some_returns_self(self):
        result = or_option(Some(1), Some(2))
        assert result.is_some()
        assert result.unwrap() == 1

    def test_nothing_returns_other(self):
        result = or_option(Nothing.empty(), Some(2))
        assert result.is_some()
        assert result.unwrap() == 2

    def test_both_nothing(self):
        result = or_option(Nothing.empty(), Nothing.empty())
        assert result.is_nothing()


class TestOrResult:
    def test_ok_returns_self(self):
        result = or_result(Ok(1), Err("fallback error"))
        assert result.is_ok()
        assert result.unwrap() == 1

    def test_err_returns_other(self):
        result = or_result(Err("primary error"), Ok(2))
        assert result.is_ok()
        assert result.unwrap() == 2

    def test_both_err(self):
        result = or_result(Err("primary"), Err("secondary"))
        assert result.is_err()
        assert result.unwrap_err() == "secondary"


class TestOk:
    def test_ok_becomes_some(self):
        result = ok(Ok(42))
        assert result.is_some()
        assert result.unwrap() == 42

    def test_err_becomes_nothing(self):
        result = ok(Err("boom"))
        assert result.is_nothing()


class TestErr:
    def test_err_becomes_some(self):
        result = err(Err("boom"))
        assert result.is_some()
        assert result.unwrap() == "boom"

    def test_ok_becomes_nothing(self):
        result = err(Ok(42))
        assert result.is_nothing()
