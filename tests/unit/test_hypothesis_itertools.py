"""
Hypothesis-based property tests for logerr.itertools collection operations.
"""

from hypothesis import given
from hypothesis import strategies as st

from logerr import Err, Nothing, Ok, Option, Result, Some
from logerr.itertools import (
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

_option_items_strategy = st.lists(
    st.one_of(st.integers().map(Some), st.just(Nothing.empty()))
)
_result_items_strategy = st.lists(
    st.one_of(
        st.integers().map(Ok), st.text().map(lambda e: Err(e, _skip_logging=True))
    )
)


class TestSequenceProperties:
    """Property-based tests for sequence_option and sequence_result."""

    @given(st.lists(st.integers()))
    def test_sequence_option_all_some_roundtrips(self, xs: list[int]):
        """sequence_option([Some(x) for x in xs]).unwrap() == xs."""
        assert sequence_option([Some(x) for x in xs]).unwrap() == xs

    @given(st.lists(st.integers()))
    def test_sequence_result_all_ok_roundtrips(self, xs: list[int]):
        """sequence_result([Ok(x) for x in xs]).unwrap() == xs."""
        assert sequence_result([Ok(x) for x in xs]).unwrap() == xs

    @given(st.lists(st.integers(), min_size=1), st.data())
    def test_sequence_option_nothing_at_any_index_short_circuits(
        self, xs: list[int], data: st.DataObject
    ):
        """Replacing any single element with Nothing makes sequence_option return Nothing."""
        index = data.draw(st.integers(min_value=0, max_value=len(xs) - 1))
        items: list[Option[int]] = [Some(x) for x in xs]
        items[index] = Nothing.empty()
        assert sequence_option(items).is_nothing()

    @given(st.lists(st.integers(), min_size=1), st.data())
    def test_sequence_result_err_at_any_index_short_circuits(
        self, xs: list[int], data: st.DataObject
    ):
        """Replacing any single element with Err makes sequence_result return Err."""
        index = data.draw(st.integers(min_value=0, max_value=len(xs) - 1))
        items: list[Result[int, str]] = [Ok(x) for x in xs]
        items[index] = Err("boom", _skip_logging=True)
        assert sequence_result(items).is_err()


class TestTraverseProperties:
    """Property-based tests for traverse_option and traverse_result."""

    @given(st.lists(st.integers()))
    def test_traverse_option_matches_map_then_sequence(self, xs: list[int]):
        """traverse_option(xs, f) == sequence_option([f(x) for x in xs])."""
        assert traverse_option(xs, lambda x: Some(x * 2)) == sequence_option(
            [Some(x * 2) for x in xs]
        )

    @given(st.lists(st.integers()))
    def test_traverse_result_matches_map_then_sequence(self, xs: list[int]):
        """traverse_result(xs, f) == sequence_result([f(x) for x in xs])."""
        assert traverse_result(xs, lambda x: Ok(x * 2)) == sequence_result(
            [Ok(x * 2) for x in xs]
        )


class TestPartitionProperties:
    """Property-based tests for partition_option and partition_result."""

    @given(_option_items_strategy)
    def test_partition_option_counts_and_values_consistent(
        self, items: list[Option[int]]
    ):
        """partition_option's values/nothing_count agree with a manual count."""
        present, nothing_count = partition_option(items)
        assert len(present) + nothing_count == len(items)
        assert nothing_count == sum(1 for item in items if item.is_nothing())
        assert present == [item.unwrap() for item in items if item.is_some()]

    @given(_result_items_strategy)
    def test_partition_result_oks_and_errs_consistent(
        self, items: list[Result[int, str]]
    ):
        """partition_result's oks/errs agree with a manual split."""
        oks, errs = partition_result(items)
        assert len(oks) + len(errs) == len(items)
        assert errs == [item.unwrap_err() for item in items if item.is_err()]
        assert oks == [item.unwrap() for item in items if item.is_ok()]


class TestValuesProperties:
    """Property-based tests for values()."""

    @given(st.lists(st.integers()))
    def test_values_all_some_roundtrips(self, xs: list[int]):
        """list(values([Some(x) for x in xs])) == xs."""
        assert list(values([Some(x) for x in xs])) == xs

    @given(_option_items_strategy)
    def test_values_mixed_matches_present_values(self, items: list[Option[int]]):
        """values() yields exactly the unwrapped values of the Some items, in order."""
        assert list(values(items)) == [
            item.unwrap() for item in items if item.is_some()
        ]


class TestPolymorphicConsistency:
    """The polymorphic sequence/traverse/partition agree with their concrete
    counterparts on non-empty, single-type input."""

    @given(st.lists(st.integers(), min_size=1))
    def test_sequence_matches_sequence_option(self, xs: list[int]):
        """sequence([Some(x) ...]) == sequence_option([Some(x) ...])."""
        items = [Some(x) for x in xs]
        assert sequence(items) == sequence_option(items)

    @given(st.lists(st.integers(), min_size=1))
    def test_sequence_matches_sequence_result(self, xs: list[int]):
        """sequence([Ok(x) ...]) == sequence_result([Ok(x) ...])."""
        items = [Ok(x) for x in xs]
        assert sequence(items) == sequence_result(items)

    @given(st.lists(st.integers(), min_size=1))
    def test_partition_matches_partition_option(self, xs: list[int]):
        """partition([Some(x) ...]) == partition_option([Some(x) ...])."""
        items = [Some(x) for x in xs]
        assert partition(items) == partition_option(items)

    @given(st.lists(st.integers(), min_size=1))
    def test_traverse_matches_traverse_option(self, xs: list[int]):
        """traverse(xs, lambda x: Some(x * 2)) == traverse_option(xs, lambda x: Some(x * 2))."""
        assert traverse(xs, lambda x: Some(x * 2)) == traverse_option(
            xs, lambda x: Some(x * 2)
        )

    @given(st.lists(st.integers(), min_size=1))
    def test_traverse_matches_traverse_result(self, xs: list[int]):
        """traverse(xs, lambda x: Ok(x * 2)) == traverse_result(xs, lambda x: Ok(x * 2))."""
        assert traverse(xs, lambda x: Ok(x * 2)) == traverse_result(
            xs, lambda x: Ok(x * 2)
        )


class TestFoldProperties:
    """Property-based tests for fold_result."""

    @given(st.lists(st.integers()))
    def test_fold_result_as_sum_matches_sum(self, xs: list[int]):
        """fold_result(xs, 0, lambda acc, x: Ok(acc + x)).unwrap() == sum(xs)."""
        assert fold_result(xs, 0, lambda acc, x: Ok(acc + x)).unwrap() == sum(xs)
