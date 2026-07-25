"""
Tests for logerr.itertools module.
"""

import pytest

from logerr import Err, Nothing, Ok, Some
from logerr.itertools import (
    fold,
    fold_option,
    fold_result,
    partition,
    partition_option,
    partition_result,
    sequence,
    sequence_option,
    sequence_result,
    traverse,
    traverse_option,
    traverse_result,
    values,
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


class TestValues:
    def test_options(self):
        assert list(values([Some(1), Nothing.empty(), Some(3)])) == [1, 3]

    def test_results(self):
        assert list(values([Ok(1), Err("boom"), Ok(3)])) == [1, 3]

    def test_all_absent(self):
        assert list(values([Nothing.empty(), Nothing.empty()])) == []

    def test_empty(self):
        assert list(values([])) == []

    def test_is_lazy(self):
        calls = []

        def gen():
            for x in [Some(1), Some(2), Some(3)]:
                calls.append(x)
                yield x

        it = values(gen())
        next(it)
        assert calls == [Some(1)]


class TestSequencePolymorphic:
    def test_dispatches_to_option(self):
        result = sequence([Some(1), Some(2)])
        assert result.is_some()
        assert result.unwrap() == [1, 2]

    def test_dispatches_to_result(self):
        result = sequence([Ok(1), Ok(2)])
        assert result.is_ok()
        assert result.unwrap() == [1, 2]

    def test_short_circuits_option(self):
        result = sequence([Some(1), Nothing.empty()])
        assert result.is_nothing()

    def test_short_circuits_result(self):
        result = sequence([Ok(1), Err("boom")])
        assert result.is_err()

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            sequence([])

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError, match="Option or Result"):
            sequence([1, 2, 3])


class TestTraversePolymorphic:
    def test_dispatches_to_option(self):
        result = traverse([1, 2, 3], lambda x: Some(x * 2))
        assert result.is_some()
        assert result.unwrap() == [2, 4, 6]

    def test_dispatches_to_result(self):
        result = traverse([1, 2, 3], lambda x: Ok(x * 2))
        assert result.is_ok()
        assert result.unwrap() == [2, 4, 6]

    def test_func_called_once_per_item(self):
        calls = []

        def func(x):
            calls.append(x)
            return Some(x)

        traverse([1, 2, 3], func)
        assert calls == [1, 2, 3]

    def test_func_called_once_per_item_result(self):
        calls = []

        def func(x):
            calls.append(x)
            return Ok(x)

        traverse([1, 2, 3], func)
        assert calls == [1, 2, 3]

    def test_short_circuits_stops_calling_func_option(self):
        calls = []

        def func(x):
            calls.append(x)
            return Nothing.empty() if x == 2 else Some(x)

        traverse([1, 2, 3, 4], func)
        assert calls == [1, 2]

    def test_short_circuits_stops_calling_func_result(self):
        calls = []

        def func(x):
            calls.append(x)
            return Err("boom") if x == 2 else Ok(x)

        traverse([1, 2, 3, 4], func)
        assert calls == [1, 2]

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            traverse([], lambda x: Some(x))

    def test_wrong_return_type_raises(self):
        with pytest.raises(TypeError, match="Option or Result"):
            traverse([1, 2, 3], lambda x: x)


class TestPartitionPolymorphic:
    def test_dispatches_to_option(self):
        values_, nothing_count = partition([Some(1), Nothing.empty()])
        assert values_ == [1]
        assert nothing_count == 1

    def test_dispatches_to_result(self):
        oks, errs = partition([Ok(1), Err("boom")])
        assert oks == [1]
        assert errs == ["boom"]

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            partition([])

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError, match="Option or Result"):
            partition([1, 2, 3])


class TestFoldOption:
    def test_all_succeed(self):
        result = fold_option([1, 2, 3], 0, lambda acc, x: Some(acc + x))
        assert result.is_some()
        assert result.unwrap() == 6

    def test_short_circuits_on_first_nothing(self):
        result = fold_option(
            [1, 2, 3], 0, lambda acc, x: Nothing.empty() if x == 2 else Some(acc + x)
        )
        assert result.is_nothing()

    def test_empty_returns_initial_unchanged(self):
        result = fold_option([], 42, lambda acc, x: Some(acc + x))
        assert result.is_some()
        assert result.unwrap() == 42

    def test_func_not_called_past_first_failure(self):
        calls = []

        def func(acc, x):
            calls.append(x)
            return Nothing.empty() if x == 2 else Some(acc + x)

        fold_option([1, 2, 3, 4], 0, func)
        assert calls == [1, 2]


class TestFoldResult:
    def test_all_succeed(self):
        result = fold_result([1, 2, 3], 0, lambda acc, x: Ok(acc + x))
        assert result.is_ok()
        assert result.unwrap() == 6

    def test_short_circuits_on_first_err(self):
        result = fold_result(
            [1, 2, 3], 0, lambda acc, x: Err("boom") if x == 2 else Ok(acc + x)
        )
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_empty_returns_initial_unchanged(self):
        result = fold_result([], 42, lambda acc, x: Ok(acc + x))
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_func_not_called_past_first_failure(self):
        calls = []

        def func(acc, x):
            calls.append(x)
            return Err("boom") if x == 2 else Ok(acc + x)

        fold_result([1, 2, 3, 4], 0, func)
        assert calls == [1, 2]


class TestFoldPolymorphic:
    def test_dispatches_to_option(self):
        result = fold([1, 2, 3], 0, lambda acc, x: Some(acc + x))
        assert result.is_some()
        assert result.unwrap() == 6

    def test_dispatches_to_result(self):
        result = fold([1, 2, 3], 0, lambda acc, x: Ok(acc + x))
        assert result.is_ok()
        assert result.unwrap() == 6

    def test_short_circuits_option(self):
        result = fold(
            [1, 2, 3], 0, lambda acc, x: Nothing.empty() if x == 2 else Some(acc + x)
        )
        assert result.is_nothing()

    def test_short_circuits_result(self):
        result = fold(
            [1, 2, 3], 0, lambda acc, x: Err("boom") if x == 2 else Ok(acc + x)
        )
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_func_called_once_per_item(self):
        calls = []

        def func(acc, x):
            calls.append(x)
            return Some(acc + x)

        fold([1, 2, 3], 0, func)
        assert calls == [1, 2, 3]

    def test_accumulator_threads_correctly(self):
        calls = []

        def func(acc, x):
            calls.append((acc, x))
            return Some(acc + x)

        result = fold([1, 2, 3], 0, func)
        assert result.unwrap() == 6
        assert calls == [(0, 1), (1, 2), (3, 3)]

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            fold([], 0, lambda acc, x: Some(acc + x))

    def test_wrong_return_type_raises(self):
        with pytest.raises(TypeError, match="Option or Result"):
            fold([1, 2, 3], 0, lambda acc, x: acc + x)
