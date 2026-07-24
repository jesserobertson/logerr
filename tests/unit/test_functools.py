"""
Tests for logerr.functools module.
"""

import pytest

from logerr import Err, Nothing, Ok, Some
from logerr.functools import zip_option, zip_result

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
