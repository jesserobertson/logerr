# `logerr.itertools` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `logerr.itertools` - `sequence`/`traverse`/`partition`/`values` collection-level operations for `Option`/`Result`, plus matching `Option.sequence`/`Option.traverse`/`Result.sequence`/`Result.traverse` classmethod factories.

**Architecture:** New core module `logerr/itertools.py` (stdlib-only, no extra deps) with six concrete type-suffixed functions (`sequence_option`, `sequence_result`, `traverse_option`, `traverse_result`, `partition_option`, `partition_result`), three `@overload`-typed polymorphic wrappers (`sequence`, `traverse`, `partition`) that dispatch on the first element's runtime type, and one dispatch-free helper (`values`). `Option`/`Result` gain `sequence`/`traverse` classmethods delegating to the concrete functions via deferred imports (matching the existing `zip`/`flatten` method pattern).

**Tech Stack:** Python 3.12+ generics (`def f[T](...)`), stdlib `itertools`/`typing.overload`, pytest, mypy strict, ruff.

## Global Constraints

- No new runtime dependencies - `logerr/itertools.py` uses only stdlib `itertools`, `collections.abc`, `typing`.
- `logerr.itertools` is NOT exported from top-level `logerr/__init__.py` - matches the existing `logerr.functools` precedent. Callers write `from logerr.itertools import sequence, ...`.
- Every function/method must have a full Google-style docstring with an `Examples:` doctest block (this repo runs `--doctest-modules logerr` in `pixi run -e dev test all`), matching the style already used throughout `logerr/functools.py`/`logerr/option.py`/`logerr/result.py`.
- `Err(...)`/`Nothing.empty()` reconstruction must use the existing no-double-log conventions: `Err(e, _skip_logging=True)` when re-wrapping an already-logged error value, `Nothing.empty()` (never preserving the original reason) on the Option side - both exactly matching `logerr/functools.py`'s existing `zip_result`/`flatten_result`/`and_result`/`zip_option`/`flatten_option`/`and_option`.
- `func` arguments passed to `traverse_*` are never wrapped in try/except - exceptions propagate uncaught, matching `map`/`then`/`filter`'s existing no-catch semantics established elsewhere in this codebase.
- Follow TDD: write the failing test, run it, watch it fail for the right reason, implement, run again, watch it pass, then commit.
- Run `pixi run -e dev pytest tests/unit/test_itertools.py -v` (or the relevant file) after each task's implementation step - do not move to the next task with a red test.
- Commit after each task using `git commit` (not `--amend`), per repo convention (see recent commit history for message style - short imperative summary line).

---

### Task 1: `sequence_option` / `sequence_result`

**Files:**
- Create: `logerr/itertools.py`
- Create: `tests/unit/test_itertools.py`

**Interfaces:**
- Produces: `sequence_option[T](items: Iterable[Option[T]]) -> Option[list[T]]`, `sequence_result[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]`. Used by Task 2 (`traverse_*` is built on top of these) and Task 5 (polymorphic `sequence()` dispatches to these).

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_itertools.py`:

```python
"""
Tests for logerr.itertools module.
"""

import pytest

from logerr import Err, Nothing, Ok, Some
from logerr.itertools import sequence_option, sequence_result

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logerr.itertools'`

- [ ] **Step 3: Write the implementation**

Create `logerr/itertools.py`:

```python
"""
Collection-level operations for Option/Result: sequence, traverse,
partition, and values - short-circuiting folds of a *collection* of
Options/Results into one, in the Haskell/Rust `traverse`/`collect` sense.

Everything else in the standard itertools toolkit (chain, filterfalse,
takewhile, ...) already works on Option/Result directly since they're
iterable (see logerr.functools) - this module only adds what plain
itertools has no equivalent for: folding many Options/Results into one
with short-circuit-on-first-failure semantics.
"""

from __future__ import annotations

from collections.abc import Iterable

from .option import Nothing, Option, Some
from .result import Err, Ok, Result


def sequence_option[T](items: Iterable[Option[T]]) -> Option[list[T]]:
    """Fold an iterable of Options into one Option of a list.

    Short-circuits on the first Nothing.

    Args:
        items: The Options to sequence.

    Returns:
        Some(values) if every item is Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> sequence_option([Some(1), Some(2), Some(3)])
        Some([1, 2, 3])
        >>> sequence_option([Some(1), Nothing.empty(), Some(3)])  # doctest: +ELLIPSIS
        Nothing(...)
        >>> sequence_option([])
        Some([])
    """
    values: list[T] = []
    for item in items:
        if item.is_nothing():
            return Nothing.empty()
        values.append(item.unwrap())
    return Some(values)


def sequence_result[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]:
    """Fold an iterable of Results into one Result of a list.

    Short-circuits on the first Err.

    Args:
        items: The Results to sequence.

    Returns:
        Ok(values) if every item is Ok, otherwise the first Err encountered.

    Examples:
        >>> from logerr import Ok, Err
        >>> sequence_result([Ok(1), Ok(2), Ok(3)])
        Ok([1, 2, 3])
        >>> sequence_result([Ok(1), Err("boom"), Ok(3)])  # doctest: +ELLIPSIS
        Err(...)
        >>> sequence_result([])
        Ok([])
    """
    values: list[T] = []
    for item in items:
        if item.is_err():
            return Err(item.unwrap_err(), _skip_logging=True)
        values.append(item.unwrap())
    return Ok(values)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add logerr/itertools.py tests/unit/test_itertools.py
git commit -m "Add sequence_option/sequence_result to logerr.itertools"
```

---

### Task 2: `traverse_option` / `traverse_result`

**Files:**
- Modify: `logerr/itertools.py`
- Modify: `tests/unit/test_itertools.py`

**Interfaces:**
- Consumes: `sequence_option`, `sequence_result` (Task 1).
- Produces: `traverse_option[T, U](items: Iterable[T], func: Callable[[T], Option[U]]) -> Option[list[U]]`, `traverse_result[T, U, E](items: Iterable[T], func: Callable[[T], Result[U, E]]) -> Result[list[U], E]`. Used by Task 5's polymorphic `traverse()`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_itertools.py` (update the import line and append classes):

```python
from logerr.itertools import (
    sequence_option,
    sequence_result,
    traverse_option,
    traverse_result,
)
```

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: FAIL with `ImportError: cannot import name 'traverse_option'`

- [ ] **Step 3: Write the implementation**

Append to `logerr/itertools.py` (add `Callable` to the `collections.abc` import):

```python
from collections.abc import Callable, Iterable
```

```python
def traverse_option[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]:
    """Map `func` over `items` and sequence the results.

    Short-circuits: `func` is never called on items after the first one
    that returns Nothing.

    Args:
        items: The values to map over.
        func: A function from T to Option[U].

    Returns:
        Some(values) if every call returns Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some
        >>> traverse_option([1, 2, 3], lambda x: Some(x * 2))
        Some([2, 4, 6])
    """
    return sequence_option(func(item) for item in items)


def traverse_result[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]:
    """Map `func` over `items` and sequence the results.

    Short-circuits: `func` is never called on items after the first one
    that returns Err.

    Args:
        items: The values to map over.
        func: A function from T to Result[U, E].

    Returns:
        Ok(values) if every call returns Ok, otherwise the first Err
        encountered.

    Examples:
        >>> from logerr import Ok
        >>> traverse_result([1, 2, 3], lambda x: Ok(x * 2))
        Ok([2, 4, 6])
    """
    return sequence_result(func(item) for item in items)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add logerr/itertools.py tests/unit/test_itertools.py
git commit -m "Add traverse_option/traverse_result to logerr.itertools"
```

---

### Task 3: `partition_option` / `partition_result`

**Files:**
- Modify: `logerr/itertools.py`
- Modify: `tests/unit/test_itertools.py`

**Interfaces:**
- Produces: `partition_option[T](items: Iterable[Option[T]]) -> tuple[list[T], int]`, `partition_result[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]`. Used by Task 5's polymorphic `partition()`.

- [ ] **Step 1: Write the failing tests**

Update the import in `tests/unit/test_itertools.py`:

```python
from logerr.itertools import (
    partition_option,
    partition_result,
    sequence_option,
    sequence_result,
    traverse_option,
    traverse_result,
)
```

Append:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: FAIL with `ImportError: cannot import name 'partition_option'`

- [ ] **Step 3: Write the implementation**

Append to `logerr/itertools.py`:

```python
def partition_option[T](items: Iterable[Option[T]]) -> tuple[list[T], int]:
    """Split an iterable of Options into present values and a Nothing count.

    Unlike sequence_option, this does not short-circuit - every item is
    visited.

    Args:
        items: The Options to partition.

    Returns:
        A tuple of (values, nothing_count).

    Examples:
        >>> from logerr import Some, Nothing
        >>> partition_option([Some(1), Nothing.empty(), Some(3)])
        ([1, 3], 1)
    """
    values: list[T] = []
    nothing_count = 0
    for item in items:
        if item.is_some():
            values.append(item.unwrap())
        else:
            nothing_count += 1
    return values, nothing_count


def partition_result[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]:
    """Split an iterable of Results into Ok values and Err values.

    Unlike sequence_result, this does not short-circuit - every item is
    visited.

    Args:
        items: The Results to partition.

    Returns:
        A tuple of (oks, errs).

    Examples:
        >>> from logerr import Ok, Err
        >>> partition_result([Ok(1), Err("boom"), Ok(3)])
        ([1, 3], ['boom'])
    """
    oks: list[T] = []
    errs: list[E] = []
    for item in items:
        if item.is_ok():
            oks.append(item.unwrap())
        else:
            errs.append(item.unwrap_err())
    return oks, errs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: PASS (20 tests)

- [ ] **Step 5: Commit**

```bash
git add logerr/itertools.py tests/unit/test_itertools.py
git commit -m "Add partition_option/partition_result to logerr.itertools"
```

---

### Task 4: `values`

**Files:**
- Modify: `logerr/itertools.py`
- Modify: `tests/unit/test_itertools.py`

**Interfaces:**
- Produces: `values[T](items: Iterable[Option[T]]) -> Iterator[T]` / `values[T](items: Iterable[Result[T, Any]]) -> Iterator[T]` (two `@overload` signatures, one implementation).

- [ ] **Step 1: Write the failing tests**

Update the import in `tests/unit/test_itertools.py` to add `values`:

```python
from logerr.itertools import (
    partition_option,
    partition_result,
    sequence_option,
    sequence_result,
    traverse_option,
    traverse_result,
    values,
)
```

Append:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: FAIL with `ImportError: cannot import name 'values'`

- [ ] **Step 3: Write the implementation**

Append to `logerr/itertools.py` (add `itertools` and `overload`/`Any` imports at the top):

```python
import itertools
from typing import Any, overload
```

```python
@overload
def values[T](items: Iterable[Option[T]]) -> Iterator[T]: ...
@overload
def values[T](items: Iterable[Result[T, Any]]) -> Iterator[T]: ...
def values(items: Iterable[Any]) -> Iterator[Any]:
    """Yield the present/Ok values from a collection of Options/Results.

    Lazy - drops Nothing/Err entries without raising or collecting error
    information. Use partition_option/partition_result if you need the
    failures too.

    Args:
        items: The Options or Results to extract values from.

    Returns:
        An iterator over the contained values.

    Examples:
        >>> from logerr import Some, Nothing
        >>> list(values([Some(1), Nothing.empty(), Some(3)]))
        [1, 3]
        >>> from logerr import Ok, Err
        >>> list(values([Ok(1), Err("boom"), Ok(3)]))
        [1, 3]
    """
    return itertools.chain.from_iterable(items)
```

Also add `Iterator` to the `collections.abc` import line:

```python
from collections.abc import Callable, Iterable, Iterator
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: PASS (25 tests)

- [ ] **Step 5: Commit**

```bash
git add logerr/itertools.py tests/unit/test_itertools.py
git commit -m "Add values() to logerr.itertools"
```

---

### Task 5: Polymorphic `sequence()` / `traverse()` / `partition()`

**Files:**
- Modify: `logerr/itertools.py`
- Modify: `tests/unit/test_itertools.py`

**Interfaces:**
- Consumes: `sequence_option`, `sequence_result`, `traverse_option` (indirectly, via calling `func` directly), `partition_option`, `partition_result` (Tasks 1-3).
- Produces: `sequence`, `traverse`, `partition` (polymorphic, `@overload`-typed). Used by Task 7's docs.

- [ ] **Step 1: Write the failing tests**

Update the import in `tests/unit/test_itertools.py`:

```python
from logerr.itertools import (
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
```

Append:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: FAIL with `ImportError: cannot import name 'sequence'`

- [ ] **Step 3: Write the implementation**

Append to `logerr/itertools.py`:

```python
@overload
def sequence[T](items: Iterable[Option[T]]) -> Option[list[T]]: ...
@overload
def sequence[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]: ...
def sequence(items: Iterable[Any]) -> Any:
    """Fold a collection of Options or Results into one.

    Dispatches on the first element's runtime type. For the unambiguous,
    always-available alternative, use sequence_option/sequence_result
    directly.

    Raises:
        ValueError: If `items` is empty.
        TypeError: If the first element is neither an Option nor a Result.

    Examples:
        >>> from logerr import Some
        >>> sequence([Some(1), Some(2)])
        Some([1, 2])
    """
    it = iter(items)
    try:
        first = next(it)
    except StopIteration:
        raise ValueError(
            "sequence() cannot infer Option vs Result from an empty "
            "iterable; use sequence_option([]) or sequence_result([]) "
            "directly"
        ) from None
    rest = itertools.chain([first], it)
    if isinstance(first, (Some, Nothing)):
        return sequence_option(rest)
    if isinstance(first, (Ok, Err)):
        return sequence_result(rest)
    raise TypeError(f"sequence() expects Option or Result items, got {type(first)!r}")


@overload
def traverse[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]: ...
@overload
def traverse[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]: ...
def traverse(items: Iterable[Any], func: Callable[[Any], Any]) -> Any:
    """Map `func` over `items` and sequence the results.

    Dispatches on the type of `func`'s first return value. `func` is
    called exactly once per item regardless of dispatch (the first call's
    result is reused, never recomputed).

    Raises:
        ValueError: If `items` is empty.
        TypeError: If `func`'s return value is neither an Option nor a
            Result.

    Examples:
        >>> from logerr import Some
        >>> traverse([1, 2, 3], lambda x: Some(x * 2))
        Some([2, 4, 6])
    """
    it = iter(items)
    try:
        first_item = next(it)
    except StopIteration:
        raise ValueError(
            "traverse() cannot infer Option vs Result from an empty "
            "iterable; use traverse_option([], func) or "
            "traverse_result([], func) directly"
        ) from None
    first_result = func(first_item)
    rest = (func(item) for item in it)
    if isinstance(first_result, (Some, Nothing)):
        return sequence_option(itertools.chain([first_result], rest))
    if isinstance(first_result, (Ok, Err)):
        return sequence_result(itertools.chain([first_result], rest))
    raise TypeError(
        "traverse() expects func to return Option or Result, "
        f"got {type(first_result)!r}"
    )


@overload
def partition[T](items: Iterable[Option[T]]) -> tuple[list[T], int]: ...
@overload
def partition[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]: ...
def partition(items: Iterable[Any]) -> tuple[list[Any], Any]:
    """Partition a collection of Options or Results.

    Dispatches on the first element's runtime type.

    Raises:
        ValueError: If `items` is empty.
        TypeError: If the first element is neither an Option nor a Result.

    Examples:
        >>> from logerr import Some, Nothing
        >>> partition([Some(1), Nothing.empty(), Some(3)])
        ([1, 3], 1)
    """
    materialized = list(items)
    if not materialized:
        raise ValueError(
            "partition() cannot infer Option vs Result from an empty "
            "iterable; use partition_option([]) or partition_result([]) "
            "directly"
        )
    first = materialized[0]
    if isinstance(first, (Some, Nothing)):
        return partition_option(materialized)
    if isinstance(first, (Ok, Err)):
        return partition_result(materialized)
    raise TypeError(f"partition() expects Option or Result items, got {type(first)!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_itertools.py -v`
Expected: PASS (39 tests)

- [ ] **Step 5: Commit**

```bash
git add logerr/itertools.py tests/unit/test_itertools.py
git commit -m "Add polymorphic sequence/traverse/partition wrappers to logerr.itertools"
```

---

### Task 6: `Option.sequence`/`Option.traverse` and `Result.sequence`/`Result.traverse` classmethods

**Files:**
- Modify: `logerr/option.py:12` (import), `logerr/option.py:405-418` (add classmethods after `from_predicate`)
- Modify: `logerr/result.py:12` (import), `logerr/result.py:396-404` (add classmethods after `from_predicate`)
- Modify: `tests/unit/test_option.py:11` (import), append new test class
- Modify: `tests/unit/test_result.py:10-11` (import), append new test class

**Interfaces:**
- Consumes: `sequence_option`, `traverse_option`, `sequence_result`, `traverse_result` (Tasks 1-2), via deferred imports inside method bodies (matching the existing `zip`/`flatten` method pattern that imports from `.functools` inline to avoid circularity).

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_option.py`, change line 11 from:

```python
from logerr import Nothing, Some, configure
```

to:

```python
from logerr import Nothing, Option, Some, configure
```

Append a new class at the end of the file:

```python
class TestOptionCollectionFactories:
    """Test that Option.sequence/Option.traverse delegate to logerr.itertools."""

    def test_sequence_all_some(self):
        result = Option.sequence([Some(1), Some(2)])
        assert result.is_some()
        assert result.unwrap() == [1, 2]

    def test_sequence_short_circuits(self):
        result = Option.sequence([Some(1), Nothing.empty()])
        assert result.is_nothing()

    def test_traverse_all_succeed(self):
        result = Option.traverse([1, 2, 3], lambda x: Some(x * 2))
        assert result.is_some()
        assert result.unwrap() == [2, 4, 6]

    def test_traverse_short_circuits(self):
        result = Option.traverse(
            [1, 2, 3], lambda x: Nothing.empty() if x == 2 else Some(x)
        )
        assert result.is_nothing()
```

In `tests/unit/test_result.py`, change line 11 from:

```python
from logerr import Err, Ok, configure
```

to:

```python
from logerr import Err, Ok, Result, configure
```

Append a new class at the end of the file:

```python
class TestResultCollectionFactories:
    """Test that Result.sequence/Result.traverse delegate to logerr.itertools."""

    def test_sequence_all_ok(self):
        result = Result.sequence([Ok(1), Ok(2)])
        assert result.is_ok()
        assert result.unwrap() == [1, 2]

    def test_sequence_short_circuits(self):
        result = Result.sequence([Ok(1), Err("boom")])
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_traverse_all_succeed(self):
        result = Result.traverse([1, 2, 3], lambda x: Ok(x * 2))
        assert result.is_ok()
        assert result.unwrap() == [2, 4, 6]

    def test_traverse_short_circuits(self):
        result = Result.traverse([1, 2, 3], lambda x: Err("boom") if x == 2 else Ok(x))
        assert result.is_err()
        assert result.unwrap_err() == "boom"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_option.py tests/unit/test_result.py -v -k "CollectionFactories"`
Expected: FAIL with `AttributeError: type object 'Option' has no attribute 'sequence'` (and similarly for `Result`)

- [ ] **Step 3: Write the implementation**

In `logerr/option.py`, change line 12 from:

```python
from collections.abc import Callable, Iterator
```

to:

```python
from collections.abc import Callable, Iterable, Iterator
```

Then in `logerr/option.py`, insert after the existing `from_predicate` classmethod (immediately before the blank lines that precede `class Some[T](Option[T]):`):

```python
    @classmethod
    def sequence(cls, items: Iterable[Option[T]]) -> Option[list[T]]:
        """Fold an iterable of Options into one Option of a list.

        Examples:
            >>> Option.sequence([Some(1), Some(2)])
            Some([1, 2])
        """
        from .itertools import sequence_option

        return sequence_option(items)

    @classmethod
    def traverse[U](
        cls, items: Iterable[U], func: Callable[[U], Option[T]]
    ) -> Option[list[T]]:
        """Map `func` over `items` and sequence the results.

        Examples:
            >>> Option.traverse([1, 2, 3], lambda x: Some(x * 2))
            Some([2, 4, 6])
        """
        from .itertools import traverse_option

        return traverse_option(items, func)
```

In `logerr/result.py`, change line 12 from:

```python
from collections.abc import Callable, Iterator
```

to:

```python
from collections.abc import Callable, Iterable, Iterator
```

Then in `logerr/result.py`, insert after the existing `from_predicate` classmethod (immediately before the blank lines that precede `class Ok[T, E](Result[T, E]):`):

```python
    @classmethod
    def sequence(cls, items: Iterable[Result[T, E]]) -> Result[list[T], E]:
        """Fold an iterable of Results into one Result of a list.

        Examples:
            >>> Result.sequence([Ok(1), Ok(2)])
            Ok([1, 2])
        """
        from .itertools import sequence_result

        return sequence_result(items)

    @classmethod
    def traverse[U](
        cls, items: Iterable[U], func: Callable[[U], Result[T, E]]
    ) -> Result[list[T], E]:
        """Map `func` over `items` and sequence the results.

        Examples:
            >>> Result.traverse([1, 2, 3], lambda x: Ok(x * 2))
            Ok([2, 4, 6])
        """
        from .itertools import traverse_result

        return traverse_result(items, func)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_option.py tests/unit/test_result.py -v`
Expected: PASS (all tests, including the new `CollectionFactories` classes)

- [ ] **Step 5: Commit**

```bash
git add logerr/option.py logerr/result.py tests/unit/test_option.py tests/unit/test_result.py
git commit -m "Add Option.sequence/traverse and Result.sequence/traverse classmethods"
```

---

### Task 7: Type stubs, docs, CHANGELOG, CLAUDE.md, final verification

**Files:**
- Create: `logerr/itertools.pyi`
- Modify: `logerr/option.pyi`
- Modify: `logerr/result.pyi`
- Create: `docs/api/itertools.md`
- Modify: `mkdocs.yml`
- Modify: `docs/guide/option-types.md`
- Modify: `docs/guide/result-types.md`
- Modify: `CHANGELOG.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: everything from Tasks 1-6 (no new production code beyond stubs in this task).

- [ ] **Step 1: Write `logerr/itertools.pyi`**

```python
"""Type stubs for logerr.itertools module."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, overload

from .option import Option
from .result import Result

def sequence_option[T](items: Iterable[Option[T]]) -> Option[list[T]]:
    """Fold an iterable of Options into one Option of a list."""
    ...

def sequence_result[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]:
    """Fold an iterable of Results into one Result of a list."""
    ...

def traverse_option[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]:
    """Map func over items and sequence the results."""
    ...

def traverse_result[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]:
    """Map func over items and sequence the results."""
    ...

def partition_option[T](items: Iterable[Option[T]]) -> tuple[list[T], int]:
    """Split an iterable of Options into present values and a Nothing count."""
    ...

def partition_result[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]:
    """Split an iterable of Results into Ok values and Err values."""
    ...

@overload
def values[T](items: Iterable[Option[T]]) -> Iterator[T]: ...
@overload
def values[T](items: Iterable[Result[T, Any]]) -> Iterator[T]: ...
@overload
def sequence[T](items: Iterable[Option[T]]) -> Option[list[T]]: ...
@overload
def sequence[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]: ...
@overload
def traverse[T, U](
    items: Iterable[T], func: Callable[[T], Option[U]]
) -> Option[list[U]]: ...
@overload
def traverse[T, U, E](
    items: Iterable[T], func: Callable[[T], Result[U, E]]
) -> Result[list[U], E]: ...
@overload
def partition[T](items: Iterable[Option[T]]) -> tuple[list[T], int]: ...
@overload
def partition[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]: ...
```

- [ ] **Step 2: Update `logerr/option.pyi`**

Change line 6 from:

```python
from collections.abc import Callable, Iterator
```

to:

```python
from collections.abc import Callable, Iterable, Iterator
```

After the existing `from_predicate` stub block (before `class Some[T](Option[T]):`), add:

```python
    @classmethod
    def sequence(cls, items: Iterable[Option[T]]) -> Option[list[T]]:
        """Fold an iterable of Options into one Option of a list."""
        ...

    @classmethod
    def traverse[U](
        cls, items: Iterable[U], func: Callable[[U], Option[T]]
    ) -> Option[list[T]]:
        """Map func over items and sequence the results."""
        ...
```

- [ ] **Step 3: Update `logerr/result.pyi`**

Change line 6 from:

```python
from collections.abc import Callable, Iterator
```

to:

```python
from collections.abc import Callable, Iterable, Iterator
```

After the existing `from_predicate` stub block (before `class Ok[T, E](Result[T, E]):`), add:

```python
    @classmethod
    def sequence(cls, items: Iterable[Result[T, E]]) -> Result[list[T], E]:
        """Fold an iterable of Results into one Result of a list."""
        ...

    @classmethod
    def traverse[U](
        cls, items: Iterable[U], func: Callable[[U], Result[T, E]]
    ) -> Result[list[T], E]:
        """Map func over items and sequence the results."""
        ...
```

- [ ] **Step 4: Run mypy to verify the stubs typecheck**

Run: `pixi run -e dev quality typecheck`
Expected: `Success: no issues found in 15 source files` (one more than the current 14, for `itertools.py`)

- [ ] **Step 5: Create `docs/api/itertools.md`**

```markdown
# Itertools

::: logerr.itertools
```

- [ ] **Step 6: Update `mkdocs.yml`**

Change:

```yaml
  - API Reference:
    - Result: api/result.md
    - Option: api/option.md
    - Configuration: api/config.md
    - Utilities: api/utilities.md
    - Functools: api/functools.md
```

to:

```yaml
  - API Reference:
    - Result: api/result.md
    - Option: api/option.md
    - Configuration: api/config.md
    - Utilities: api/utilities.md
    - Functools: api/functools.md
    - Itertools: api/itertools.md
```

- [ ] **Step 7: Update `docs/guide/option-types.md`**

After the existing "`zip()`, `flatten()`, `and_()`, `or_()` - Additional Combinators" section (right after its closing `itertools`-interop code block, before "## Method Chaining"), add:

```markdown
### Collecting Options: `sequence()` and `traverse()`

```python
from logerr import Option, Some, Nothing

# sequence() - fold a list of Options into one Option of a list
Option.sequence([Some(1), Some(2), Some(3)])   # Some([1, 2, 3])
Option.sequence([Some(1), Nothing.empty()])    # Nothing

# traverse() - map a function returning Option over a list, then sequence
Option.traverse([1, 2, 3], lambda x: Some(x * 2))  # Some([2, 4, 6])
```

Free functions with the same behavior are also available from
`logerr.itertools` (`sequence_option`, `traverse_option`), along with
`partition_option()` (collects every present value *and* a count of how
many were `Nothing`, without short-circuiting) and `values()` (a named
wrapper around the `itertools.chain.from_iterable` trick below):

```python
from logerr.itertools import partition_option, sequence_option, values

partition_option([Some(1), Nothing.empty(), Some(3)])  # ([1, 3], 1)

# itertools.chain.from_iterable already "flattens to just the present
# values" for free, since Option is iterable - values() just names it:
list(values([Some(1), Nothing.empty(), Some(3)]))      # [1, 3]
```
```

- [ ] **Step 8: Update `docs/guide/result-types.md`**

After the existing "`zip()`, `flatten()`, `and_()`, `or_()`, `ok()`, `err()` - Additional Combinators" section (right after its closing `itertools`-interop code block, before "## Method Chaining"), add:

```markdown
### Collecting Results: `sequence()` and `traverse()`

```python
from logerr import Result, Ok, Err

# sequence() - fold a list of Results into one Result of a list
Result.sequence([Ok(1), Ok(2), Ok(3)])   # Ok([1, 2, 3])
Result.sequence([Ok(1), Err("boom")])    # Err("boom")

# traverse() - map a function returning Result over a list, then sequence
Result.traverse([1, 2, 3], lambda x: Ok(x * 2))  # Ok([2, 4, 6])
```

Free functions with the same behavior are also available from
`logerr.itertools` (`sequence_result`, `traverse_result`), along with
`partition_result()` (collects every Ok value *and* every Err value,
without short-circuiting) and `values()` (a named wrapper around the
`itertools.chain.from_iterable` trick below):

```python
from logerr.itertools import partition_result, sequence_result, values

partition_result([Ok(1), Err("boom"), Ok(3)])  # ([1, 3], ['boom'])

# itertools.chain.from_iterable already "flattens to just the Ok values"
# for free, since Result is iterable - values() just names it:
list(values([Ok(1), Err("boom"), Ok(3)]))      # [1, 3]
```
```

- [ ] **Step 9: Update `CHANGELOG.md`**

In the `### Added` section, after the `__iter__` bullet (the one ending "...that could behave differently from the real one depending on what you pass it.") and before "- `CHANGELOG.md` (this file).", insert:

```markdown
- `logerr.itertools` - collection-level operations that plain `itertools`
  has no equivalent for: `sequence_option`/`sequence_result` (fold a
  collection of Options/Results into one, short-circuiting on the first
  failure), `traverse_option`/`traverse_result` (map then sequence, never
  calling the function past the first failure), `partition_option`/
  `partition_result` (split into successes/failures without
  short-circuiting), and `values` (a named wrapper for the
  `itertools.chain.from_iterable` "flatten to just the present/Ok values"
  trick). `sequence`/`traverse`/`partition` also have `@overload`-typed
  polymorphic wrappers that dispatch on runtime type, raising `ValueError`
  on empty input (ambiguous - use the `_option`/`_result` function
  directly instead). `Option`/`Result` gained matching `sequence()`/
  `traverse()` classmethod factories.
```

- [ ] **Step 10: Update `CLAUDE.md`**

After the existing "Combinator Methods on Option/Result" section (after its last paragraph ending "...depending on what you pass it.", before "## API Structure"), add:

```markdown
### **Collection Operations: `logerr.itertools`**

`logerr.itertools` adds what plain `itertools` has no equivalent for -
folding a *collection* of `Option`/`Result` values into one, with
short-circuit-on-first-failure semantics: `sequence_option`/
`sequence_result`, `traverse_option`/`traverse_result` (map then sequence,
short-circuiting), and `partition_option`/`partition_result` (collect
successes *and* failures, no short-circuit). `sequence`/`traverse`/
`partition` also exist as `@overload`-typed polymorphic wrappers
dispatching on runtime type (raising `ValueError` on empty input, since
there's no element to dispatch on - use the `_option`/`_result` function
directly in that case). `values()` names the existing free
`itertools.chain.from_iterable` interop trick (flatten to just the
present/Ok values). `Option.sequence`/`Option.traverse` and
`Result.sequence`/`Result.traverse` classmethod factories delegate to the
free functions, mirroring the existing `Option.from_nullable`/`Result.of`
classmethod-factory pattern.
```

- [ ] **Step 11: Run full verification**

Run: `pixi run -e dev check-all`
Expected: all tests pass (unit, integration, doctests including the new guide/CHANGELOG/CLAUDE.md examples), mypy clean on 15 source files, ruff/format clean, version sync clean.

- [ ] **Step 12: Commit**

```bash
git add logerr/itertools.pyi logerr/option.pyi logerr/result.pyi docs/api/itertools.md mkdocs.yml docs/guide/option-types.md docs/guide/result-types.md CHANGELOG.md CLAUDE.md
git commit -m "Add type stubs and docs for logerr.itertools"
```

---

### Task 8: Functional-programming showcase (quicksort, BST, red-black tree)

**Files:**
- Create: `docs/guide/functional-examples.md`
- Modify: `mkdocs.yml`

**Interfaces:**
- Consumes: `Result.traverse` (Task 6), `Ok`/`Err`/`Some`/`Nothing`/`Option`/`Result` (existing), `match`/`case` structural pattern matching (existing language feature, already documented elsewhere in the guide).

This task adds a capstone documentation page showing classic functional-programming algorithms written in `logerr`'s style: quicksort (using `Result.traverse` for validation + `.map()` for the pure algorithm), a simplified `Option`-based binary search tree (using `Result` for duplicate-key detection), and then a red-black tree extension of the same BST (Okasaki's purely-functional insertion algorithm - the standard reference implementation for immutable red-black trees, translated from its usual `Empty`/`Tree` ADT into `Nothing`/`Some(RBNode(...))`). This is plain narrative documentation - the code blocks use plain ` ```python ` fences (not `>>>` doctest syntax), matching the existing "Method Chaining"/"Real-World Example" sections of `option-types.md`/`result-types.md`, so it is not picked up by `--doctest-modules`/`--doctest-glob=*.md` collection. It is still real, runnable code - Step 3 below verifies it by hand before committing.

- [ ] **Step 1: Write `docs/guide/functional-examples.md`**

```markdown
# Functional Programming Examples

This page walks through a few classic functional-programming algorithms
implemented in `logerr`'s style, to show `Option`/`Result`/`match`-`case`/
`logerr.itertools` working together on something more substantial than a
config-loading pipeline.

## Quicksort

The sorting logic itself can't fail, so plain quicksort doesn't need
`Option`/`Result` at all - it's the textbook recursive partition-and-recurse
definition:

```python
def quicksort[T](items: list[T]) -> list[T]:
    """Classic functional quicksort: partition around a pivot, recurse."""
    if not items:
        return []
    pivot, *rest = items
    smaller = [x for x in rest if x < pivot]
    larger = [x for x in rest if x >= pivot]
    return quicksort(smaller) + [pivot] + quicksort(larger)
```

A more realistic version validates its input first - `Result.traverse`
(from Task 6 of this plan) checks every element and short-circuits on the
first one that fails, then `.map()` chains the pure sort onto the
validated list:

```python
from logerr import Ok, Err, Result

def safe_quicksort(raw: list[object]) -> Result[list[int], str]:
    """Validate every element is an int, then quicksort.

    Result.traverse short-circuits on the first non-int - quicksort is
    never called on invalid input.
    """
    return Result.traverse(
        raw,
        lambda x: Ok(x) if isinstance(x, int) else Err(f"Not an int: {x!r}"),
    ).map(quicksort)

safe_quicksort([3, 1, 4, 1, 5])        # Ok([1, 1, 3, 4, 5])
safe_quicksort([3, 1, "oops", 5])      # Err("Not an int: 'oops'")
```

## A Binary Search Tree, `Option`-shaped

A BST node's children are either present or absent - exactly what `Option`
models. Insertion can fail (duplicate key), which is exactly what `Result`
models:

```python
from dataclasses import dataclass
from logerr import Option, Some, Nothing, Result, Ok, Err

@dataclass
class Node[T]:
    value: T
    left: "Option[Node[T]]"
    right: "Option[Node[T]]"

def leaf[T](value: T) -> Node[T]:
    return Node(value, Nothing.empty(), Nothing.empty())

def insert[T](tree: Option[Node[T]], value: T) -> Result[Node[T], str]:
    match tree:
        case Nothing():
            return Ok(leaf(value))
        case Some(node) if value == node.value:
            return Err(f"Duplicate key: {value}")
        case Some(node) if value < node.value:
            return insert(node.left, value).map(
                lambda new_left: Node(node.value, Some(new_left), node.right)
            )
        case Some(node):
            return insert(node.right, value).map(
                lambda new_right: Node(node.value, node.left, Some(new_right))
            )

def search[T](tree: Option[Node[T]], value: T) -> Option[T]:
    match tree:
        case Nothing():
            return Nothing.empty()
        case Some(node) if value == node.value:
            return Some(node.value)
        case Some(node) if value < node.value:
            return search(node.left, value)
        case Some(node):
            return search(node.right, value)
```

Building a tree from a list of values is a *fold*, not a `traverse`: each
insertion depends on the tree built by the previous one, whereas
`traverse` assumes each item maps independently. So this uses a plain loop
with `match`/`case`, short-circuiting manually on the first `Err`:

```python
def build_tree[T](values: list[T]) -> Result[Option[Node[T]], str]:
    tree: Option[Node[T]] = Nothing.empty()
    for v in values:
        match insert(tree, v):
            case Ok(new_node):
                tree = Some(new_node)
            case Err() as e:
                return e
    return Ok(tree)

build_tree([5, 3, 8, 1, 4])   # Ok(Some(Node(value=5, ...)))
build_tree([5, 3, 5])         # Err('Duplicate key: 5')
```

## Adding Balance: a Red-Black Tree

The BST above can degenerate into a linked list on sorted input. Red-black
trees fix this with a coloring invariant, rebalanced on every insert.
Okasaki's purely-functional insertion algorithm (*Purely Functional Data
Structures*, 1999) is the standard reference for this without mutation or
parent pointers - just four pattern-matched rebalancing cases and a
fallback. It translates almost directly into `logerr`'s style, since
Python's `match`/`case` can destructure nested `Some(RBNode(...))`
patterns the same way Okasaki's ML/Haskell original destructures its
`Tree` constructor:

```python
from dataclasses import dataclass
from enum import Enum, auto
from logerr import Option, Some, Nothing, Result, Ok, Err

class Color(Enum):
    RED = auto()
    BLACK = auto()

@dataclass
class RBNode[T]:
    color: Color
    left: "Option[RBNode[T]]"
    value: T
    right: "Option[RBNode[T]]"

def _balance[T](
    color: Color,
    left: Option[RBNode[T]],
    value: T,
    right: Option[RBNode[T]],
) -> RBNode[T]:
    """The four Okasaki rebalancing cases, plus a fallback."""
    match (color, left, value, right):
        case (
            Color.BLACK,
            Some(RBNode(Color.RED, Some(RBNode(Color.RED, a, x, b)), y, c)),
            z,
            d,
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case (
            Color.BLACK,
            Some(RBNode(Color.RED, a, x, Some(RBNode(Color.RED, b, y, c)))),
            z,
            d,
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case (
            Color.BLACK,
            a,
            x,
            Some(RBNode(Color.RED, Some(RBNode(Color.RED, b, y, c)), z, d)),
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case (
            Color.BLACK,
            a,
            x,
            Some(RBNode(Color.RED, b, y, Some(RBNode(Color.RED, c, z, d)))),
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case _:
            return RBNode(color, left, value, right)

def _ins[T](node: Option[RBNode[T]], value: T) -> Result[RBNode[T], str]:
    match node:
        case Nothing():
            return Ok(RBNode(Color.RED, Nothing.empty(), value, Nothing.empty()))
        case Some(n) if value == n.value:
            return Err(f"Duplicate key: {value}")
        case Some(n) if value < n.value:
            return _ins(n.left, value).map(
                lambda new_left: _balance(n.color, Some(new_left), n.value, n.right)
            )
        case Some(n):
            return _ins(n.right, value).map(
                lambda new_right: _balance(n.color, n.left, n.value, Some(new_right))
            )

def rb_insert[T](tree: Option[RBNode[T]], value: T) -> Result[Option[RBNode[T]], str]:
    """Insert into a red-black tree, keeping the same Result-based
    duplicate-key contract as the plain BST above."""
    return _ins(tree, value).map(
        lambda n: Some(RBNode(Color.BLACK, n.left, n.value, n.right))
    )
```

Same recursive shape as the plain BST's `insert` - `Nothing`/`Some` for
absent/present children, `Result`/`.map()` for duplicate-key
short-circuiting - with `_balance`'s four `match`/`case` arms doing the
rebalancing work that `insert` alone doesn't need. Building a tree from a
list works the same way as `build_tree` above, just calling `rb_insert`
instead of `insert`.
```

- [ ] **Step 2: Update `mkdocs.yml`**

Change:

```yaml
  - User Guide:
    - Getting Started: guide/getting-started.md
    - Result Types: guide/result-types.md
    - Option Types: guide/option-types.md
    - Configuration: guide/configuration.md
    - Examples: guide/examples.md
```

to:

```yaml
  - User Guide:
    - Getting Started: guide/getting-started.md
    - Result Types: guide/result-types.md
    - Option Types: guide/option-types.md
    - Configuration: guide/configuration.md
    - Examples: guide/examples.md
    - Functional Programming Examples: guide/functional-examples.md
```

- [ ] **Step 3: Manually verify the examples actually run**

This page's code blocks are plain ` ```python ` fences, not `>>>` doctests,
so they aren't covered by `pixi run -e dev test all`'s automatic
doctest collection. Verify by hand before committing - copy each code
block (quicksort, `safe_quicksort`, the BST's `insert`/`search`/
`build_tree`, and the red-black tree's `_balance`/`_ins`/`rb_insert`) into
a scratch file and run it:

```bash
python -c "
from dataclasses import dataclass
from enum import Enum, auto
from logerr import Option, Some, Nothing, Result, Ok, Err

# ... paste quicksort, safe_quicksort, Node/leaf/insert/search/build_tree,
# Color/RBNode/_balance/_ins/rb_insert here ...

assert safe_quicksort([3, 1, 4, 1, 5]).unwrap() == [1, 1, 3, 4, 5]
assert safe_quicksort([3, 1, 'oops', 5]).is_err()

t = build_tree([5, 3, 8, 1, 4])
assert t.is_ok()
assert search(t.unwrap(), 4).unwrap() == 4
assert search(t.unwrap(), 99).is_nothing()
assert build_tree([5, 3, 5]).is_err()

rbt: Option = Nothing.empty()
for v in [5, 3, 8, 1, 4, 7, 9, 2, 6, 0]:
    rbt = rb_insert(rbt, v).unwrap()
def rb_search(tree, value):
    match tree:
        case Nothing():
            return Nothing.empty()
        case Some(n) if value == n.value:
            return Some(n.value)
        case Some(n) if value < n.value:
            return rb_search(n.left, value)
        case Some(n):
            return rb_search(n.right, value)
for v in [5, 3, 8, 1, 4, 7, 9, 2, 6, 0]:
    assert rb_search(rbt, v).unwrap() == v
assert rb_search(rbt, 99).is_nothing()
print('all examples verified')
"
```

Expected: `all examples verified` with no `AssertionError`/exception. If
the red-black tree assertions fail, re-check the four `_balance` match
patterns against Okasaki's original (each should combine a red
grandparent-red-parent chain on one of the four sides into one red node
with two black children) before touching anything else - a single
transposed `left`/`right` in one of the four cases is the most likely
mistake, not a deeper logic error.

- [ ] **Step 4: Run full verification**

Run: `pixi run -e dev check-all`
Expected: unchanged from Task 7 Step 11 (this page's code isn't part of
doctest collection) - all tests still pass, mypy/ruff/format/version-sync
still clean.

- [ ] **Step 5: Commit and push**

```bash
git add docs/guide/functional-examples.md mkdocs.yml
git commit -m "Add functional programming showcase (quicksort, BST, red-black tree)"
git push origin main
```

---

## Self-Review Notes

- **Spec coverage:** all 6 concrete functions (Tasks 1-3), `values` (Task 4), all 3 polymorphic wrappers (Task 5), all 4 classmethod factories (Task 6), `.pyi` stubs + docs + CHANGELOG + CLAUDE.md (Task 7). Matches every section of `docs/superpowers/specs/2026-07-24-itertools-design.md`. `partition`/`values` deliberately have no classmethod factory, per spec. Task 8 (quicksort/BST/red-black tree showcase) was added mid-plan at the user's request, after the spec was written - it's documentation-only, uses no new production API beyond what Tasks 1-7 already deliver (`Result.traverse`, `.map()`, `match`/`case`), and is verified by hand (Step 3) since its code blocks are plain fences, not doctests.
- **Placeholder scan:** none found - every step has complete, runnable code.
- **Type consistency:** `sequence_option`/`sequence_result`/`traverse_option`/`traverse_result`/`partition_option`/`partition_result` signatures are identical across the spec, Task 1-3 implementations, Task 7's `.pyi` stub, and the classmethod delegations in Task 6 - checked side by side. `values`' two-overload shape matches between `itertools.py` (Task 4) and `itertools.pyi` (Task 7).
- **Traverse short-circuit correctness:** `traverse_option`/`traverse_result` are implemented as `sequence_*(func(item) for item in items)` - a generator expression, so `sequence_*`'s early `return` on the first failure means the generator is simply abandoned, and `func` is never invoked for items after that point. Verified by the `test_func_not_called_past_first_failure` tests in Task 2.
- **Polymorphic `traverse()` calls `func` exactly once per item:** the wrapper calls `func(first_item)` once to detect the Option-vs-Result branch, then reuses that already-computed result via `itertools.chain([first_result], rest)` rather than recomputing it - verified by Task 5's `test_func_called_once_per_item`.
