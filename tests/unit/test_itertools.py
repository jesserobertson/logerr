"""
Tests for logerr.itertools module.
"""

import pytest

from logerr import Err, Nothing, Ok, Some
from logerr.itertools import (
    partition_option,
    partition_result,
    sequence_option,
    sequence_result,
    traverse_option,
    traverse_result,
)

pytestmark = pytest.mark.unit


class TestSequenceOption:
    def test_all_some(self):
        result = sequence_option([Some(1), Some(2), Some(3)])
        assert result.is_some()
        assert result.unwrap() == [1, 2, 3]

    def test_short_circuits_on_first_nothing(self):
        result = sequence_option([Some(1), Nothing.empty(), Some(3)])
        assert result.is_nothing()

    def test_empty(self):
        result = sequence_option([])
        assert result.is_some()
        assert result.unwrap() == []


class TestSequenceResult:
    def test_all_ok(self):
        result = sequence_result([Ok(1), Ok(2), Ok(3)])
        assert result.is_ok()
        assert result.unwrap() == [1, 2, 3]

    def test_short_circuits_on_first_err(self):
        result = sequence_result([Ok(1), Err("boom"), Ok(3)])
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_empty(self):
        result = sequence_result([])
        assert result.is_ok()
        assert result.unwrap() == []


class TestTraverseOption:
    def test_all_succeed(self):
        result = traverse_option([1, 2, 3], lambda x: Some(x * 2))
        assert result.is_some()
        assert result.unwrap() == [2, 4, 6]

    def test_short_circuits_on_first_nothing(self):
        result = traverse_option(
            [1, 2, 3], lambda x: Nothing.empty() if x == 2 else Some(x)
        )
        assert result.is_nothing()

    def test_func_not_called_past_first_failure(self):
        calls = []

        def func(x):
            calls.append(x)
            return Nothing.empty() if x == 2 else Some(x)

        traverse_option([1, 2, 3, 4], func)
        assert calls == [1, 2]


class TestTraverseResult:
    def test_all_succeed(self):
        result = traverse_result([1, 2, 3], lambda x: Ok(x * 2))
        assert result.is_ok()
        assert result.unwrap() == [2, 4, 6]

    def test_short_circuits_on_first_err(self):
        result = traverse_result([1, 2, 3], lambda x: Err("boom") if x == 2 else Ok(x))
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_func_not_called_past_first_failure(self):
        calls = []

        def func(x):
            calls.append(x)
            return Err("boom") if x == 2 else Ok(x)

        traverse_result([1, 2, 3, 4], func)
        assert calls == [1, 2]


class TestPartitionOption:
    def test_mixed(self):
        values, nothing_count = partition_option([Some(1), Nothing.empty(), Some(3)])
        assert values == [1, 3]
        assert nothing_count == 1

    def test_all_some(self):
        values, nothing_count = partition_option([Some(1), Some(2)])
        assert values == [1, 2]
        assert nothing_count == 0

    def test_all_nothing(self):
        values, nothing_count = partition_option([Nothing.empty(), Nothing.empty()])
        assert values == []
        assert nothing_count == 2

    def test_visits_every_item(self):
        values, nothing_count = partition_option(
            [Nothing.empty(), Some(1), Nothing.empty(), Some(2), Nothing.empty()]
        )
        assert values == [1, 2]
        assert nothing_count == 3


class TestPartitionResult:
    def test_mixed(self):
        oks, errs = partition_result([Ok(1), Err("boom"), Ok(3)])
        assert oks == [1, 3]
        assert errs == ["boom"]

    def test_all_ok(self):
        oks, errs = partition_result([Ok(1), Ok(2)])
        assert oks == [1, 2]
        assert errs == []

    def test_all_err(self):
        oks, errs = partition_result([Err("a"), Err("b")])
        assert oks == []
        assert errs == ["a", "b"]

    def test_visits_every_item(self):
        oks, errs = partition_result([Err("a"), Ok(1), Err("b"), Ok(2)])
        assert oks == [1, 2]
        assert errs == ["a", "b"]
