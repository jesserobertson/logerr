# logerr.functools Combinators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `zip`, `flatten`, `and_`, `or_`, `ok`, `err` combinators to `Option`/`Result`, implemented as free functions in a new `logerr/functools.py` module with thin delegating methods on the classes.

**Architecture:** 10 free functions in `logerr/functools.py` (no callable execution, so no exception-catch-vs-propagate concern — pure value combinators using only each type's existing public API: `is_some()`/`is_nothing()`/`is_ok()`/`is_err()`/`unwrap()`/`unwrap_err()`, never private `_value`/`_error`/`_reason`). `Option`/`Result` gain matching instance methods that call straight through to these functions.

`Some`/`Nothing`/`Ok`/`Err` also gain `__iter__` (yielding the contained value 0 or 1 times — matching Rust's own `Option::iter()`/`Result::iter()`, which exist specifically so `Option`/`Result` compose with the standard iterator toolkit). This means Python's own `zip()` already works correctly on `Option`/`Result` values for free once they're iterable — no bespoke polymorphic wrapper needed, and no risk of a `logerr` `zip()` behaving differently from the real one depending on what you hand it. `zip_option`/`zip_result` (and the `.zip()` method) stay clearly separate, explicitly-named functions for "combine two Options/Results into one Option/Result of a tuple" — a distinct, opt-in operation, not a competing `zip`. Operating across *collections* of Options/Results (e.g. zipping two lists of Results into one Result of a list, short-circuiting on the first error) is deferred to a future `logerr.itertools` spec alongside `sequence`/`traverse` — out of scope here.

**Tech Stack:** Python 3.12+ generic syntax (`def f[T](...)`), pytest, mypy strict.

## Global Constraints

- No private attribute access (`_value`, `_error`, `_reason`, `_exception`) from `logerr/functools.py` — only the public API each class already exposes.
- When a function must construct a fresh `Err`/`Nothing` to satisfy a different type parameter than the input had, pass `_skip_logging=True` on `Err` (its constructor logs by default; the original was already logged) — this exact pattern already exists in `Err.then()`/`Err.map()`/`Nothing.then()`/`Nothing.map()`, follow it.
- `mypy logerr` must stay clean under `strict = true` (already the project's config) after every task.
- `ruff check`/`ruff format --check` must stay clean after every task (project's ruff select list: `E,W,F,I,B,C4,UP,SIM,RUF,N,PTH`).
- Follow existing docstring style exactly: Google-style `Args:`/`Returns:`/`Examples:` with `>>>` doctests that actually run (this repo's `test all` executes `--doctest-modules logerr`).

---

### Task 1: `zip_option` and `zip_result`

**Files:**
- Create: `logerr/functools.py`
- Create: `tests/unit/test_functools.py`

**Interfaces:**
- Consumes: `Option`/`Some`/`Nothing` from `logerr.option`; `Result`/`Ok`/`Err` from `logerr.result`.
- Produces: `zip_option[T, U](a: Option[T], b: Option[U]) -> Option[tuple[T, U]]`, `zip_result[T, U, E](a: Result[T, E], b: Result[U, E]) -> Result[tuple[T, U], E]`. Task 5 calls `zip_option` from `Option.zip()`; Task 6 calls `zip_result` from `Result.zip()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_functools.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logerr.functools'`

- [ ] **Step 3: Write minimal implementation**

Create `logerr/functools.py`:

```python
"""
Functional combinators for Option/Result, mirroring Rust's Option/Result
API surface (zip, flatten, and, or, ok, err).

These are pure value combinators - none of them invoke a user-supplied
callable, so there is no exception to catch: a Nothing/Err input just
propagates, matching the corresponding value's existing state. All
functions here use only the public API of Option/Result
(is_some/is_nothing/is_ok/is_err/unwrap/unwrap_err) - never private
_value/_error/_reason attributes.

Note there's no bespoke "polymorphic zip" here: Some/Nothing/Ok/Err are
iterable (see Task 5/6 in the implementation plan), yielding their value
0 or 1 times, so Python's own builtins.zip() already works correctly on
them directly - no wrapper needed, and no risk of a logerr zip() behaving
differently from the real one. zip_option/zip_result below are a
deliberately distinct, explicitly-named operation: combining two
Options/Results into one Option/Result of a tuple.
"""

from __future__ import annotations

from .option import Nothing, Option, Some
from .result import Err, Ok, Result


def zip_option[T, U](a: Option[T], b: Option[U]) -> Option[tuple[T, U]]:
    """Combine two Options into an Option of a tuple.

    Args:
        a: The first Option.
        b: The second Option.

    Returns:
        Some((a_value, b_value)) if both are Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> zip_option(Some(1), Some("a"))
        Some((1, 'a'))
        >>> zip_option(Nothing.empty(), Some("a"))
        Nothing('Empty option')
    """
    if a.is_some() and b.is_some():
        return Some((a.unwrap(), b.unwrap()))
    return Nothing.empty()


def zip_result[T, U, E](a: Result[T, E], b: Result[U, E]) -> Result[tuple[T, U], E]:
    """Combine two Results into a Result of a tuple.

    Args:
        a: The first Result.
        b: The second Result.

    Returns:
        Ok((a_value, b_value)) if both are Ok, otherwise the first Err
        encountered (checking a before b).

    Examples:
        >>> from logerr import Ok, Err
        >>> zip_result(Ok(1), Ok("a"))
        Ok((1, 'a'))
        >>> zip_result(Err("boom"), Ok("a"))  # doctest: +ELLIPSIS
        Err(...)
    """
    if a.is_err():
        return Err(a.unwrap_err(), _skip_logging=True)
    if b.is_err():
        return Err(b.unwrap_err(), _skip_logging=True)
    return Ok((a.unwrap(), b.unwrap()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v`
Expected: 8 passed

- [ ] **Step 5: Run quality checks**

Run: `pixi run -e dev quality`
Expected: mypy/ruff/format all pass (fix any issues before continuing)

- [ ] **Step 6: Commit**

```bash
git add logerr/functools.py tests/unit/test_functools.py
git commit -m "Add zip_option/zip_result combinators in logerr.functools"
```

---

### Task 2: `flatten_option` and `flatten_result`

**Files:**
- Modify: `logerr/functools.py`
- Modify: `tests/unit/test_functools.py`

**Interfaces:**
- Consumes: same as Task 1.
- Produces: `flatten_option[T](nested: Option[Option[T]]) -> Option[T]`, `flatten_result[T, E](nested: Result[Result[T, E], E]) -> Result[T, E]`. Used by Tasks 3/4's `.flatten()` methods.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_functools.py`:

```python
from logerr.functools import flatten_option, flatten_result


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v -k Flatten`
Expected: FAIL with `ImportError: cannot import name 'flatten_option'`

- [ ] **Step 3: Write minimal implementation**

Add to `logerr/functools.py` (after `zip_result`):

```python
def flatten_option[T](nested: Option[Option[T]]) -> Option[T]:
    """Flatten a nested Option by one level.

    Args:
        nested: An Option containing another Option.

    Returns:
        The inner Option if the outer is Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> flatten_option(Some(Some(42)))
        Some(42)
        >>> flatten_option(Nothing.empty())
        Nothing('Empty option')
    """
    if nested.is_some():
        return nested.unwrap()
    return Nothing.empty()


def flatten_result[T, E](nested: Result[Result[T, E], E]) -> Result[T, E]:
    """Flatten a nested Result by one level.

    Args:
        nested: A Result containing another Result, sharing the same
            error type.

    Returns:
        The inner Result if the outer is Ok, otherwise the outer Err.

    Examples:
        >>> from logerr import Ok, Err
        >>> flatten_result(Ok(Ok(42)))
        Ok(42)
        >>> flatten_result(Err("outer boom"))  # doctest: +ELLIPSIS
        Err(...)
    """
    if nested.is_err():
        return Err(nested.unwrap_err(), _skip_logging=True)
    return nested.unwrap()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v`
Expected: 14 passed

- [ ] **Step 5: Run quality checks**

Run: `pixi run -e dev quality`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add logerr/functools.py tests/unit/test_functools.py
git commit -m "Add flatten_option/flatten_result combinators"
```

---

### Task 3: `and_option`/`and_result` and `or_option`/`or_result`

**Files:**
- Modify: `logerr/functools.py`
- Modify: `tests/unit/test_functools.py`

**Interfaces:**
- Consumes: same as Task 1.
- Produces: `and_option[T, U](opt: Option[T], other: Option[U]) -> Option[U]`, `and_result[T, U, E](res: Result[T, E], other: Result[U, E]) -> Result[U, E]`, `or_option[T](opt: Option[T], other: Option[T]) -> Option[T]`, `or_result[T, E, F](res: Result[T, E], other: Result[T, F]) -> Result[T, F]`. Used by Tasks 3/4 (note: this task number now covers both the option and result method-adding tasks below, renumbered as Tasks 4/5) `.and_()`/`.or_()` methods.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_functools.py`:

```python
from logerr.functools import and_option, and_result, or_option, or_result


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v -k "And or Or"`
Expected: FAIL with `ImportError: cannot import name 'and_option'`

- [ ] **Step 3: Write minimal implementation**

Add to `logerr/functools.py` (after `flatten_result`):

```python
def and_option[T, U](opt: Option[T], other: Option[U]) -> Option[U]:
    """Return `other` if `opt` is Some, otherwise Nothing.

    Args:
        opt: The Option to check.
        other: The Option to return if `opt` is Some.

    Returns:
        `other` if `opt` is Some, otherwise Nothing.

    Examples:
        >>> from logerr import Some, Nothing
        >>> and_option(Some(1), Some("a"))
        Some('a')
        >>> and_option(Nothing.empty(), Some("a"))
        Nothing('Empty option')
    """
    if opt.is_some():
        return other
    return Nothing.empty()


def and_result[T, U, E](res: Result[T, E], other: Result[U, E]) -> Result[U, E]:
    """Return `other` if `res` is Ok, otherwise the original Err.

    Args:
        res: The Result to check.
        other: The Result to return if `res` is Ok.

    Returns:
        `other` if `res` is Ok, otherwise `res`'s error re-wrapped.

    Examples:
        >>> from logerr import Ok, Err
        >>> and_result(Ok(1), Ok("a"))
        Ok('a')
        >>> and_result(Err("boom"), Ok("a"))  # doctest: +ELLIPSIS
        Err(...)
    """
    if res.is_err():
        return Err(res.unwrap_err(), _skip_logging=True)
    return other


def or_option[T](opt: Option[T], other: Option[T]) -> Option[T]:
    """Return `opt` if it's Some, otherwise `other`.

    Args:
        opt: The Option to check.
        other: The fallback Option if `opt` is Nothing.

    Returns:
        `opt` if Some, otherwise `other`.

    Examples:
        >>> from logerr import Some, Nothing
        >>> or_option(Some(1), Some(2))
        Some(1)
        >>> or_option(Nothing.empty(), Some(2))
        Some(2)
    """
    if opt.is_some():
        return opt
    return other


def or_result[T, E, F](res: Result[T, E], other: Result[T, F]) -> Result[T, F]:
    """Return `res` if it's Ok, otherwise `other`.

    Args:
        res: The Result to check.
        other: The fallback Result if `res` is Err. May have a different
            error type than `res`.

    Returns:
        `res`'s value re-wrapped if Ok, otherwise `other`.

    Examples:
        >>> from logerr import Ok, Err
        >>> or_result(Ok(1), Err("fallback"))
        Ok(1)
        >>> or_result(Err("primary"), Ok(2))
        Ok(2)
    """
    if res.is_ok():
        return Ok(res.unwrap())
    return other
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v`
Expected: 26 passed

- [ ] **Step 5: Run quality checks**

Run: `pixi run -e dev quality`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add logerr/functools.py tests/unit/test_functools.py
git commit -m "Add and_/or_ combinators for Option and Result"
```

---

### Task 4: `ok` and `err`

**Files:**
- Modify: `logerr/functools.py`
- Modify: `tests/unit/test_functools.py`

**Interfaces:**
- Consumes: same as Task 1.
- Produces: `ok[T, E](result: Result[T, E]) -> Option[T]`, `err[T, E](result: Result[T, E]) -> Option[E]`. Used by Task 5's `.ok()`/`.err()` methods.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_functools.py`:

```python
from logerr.functools import err, ok


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v -k "TestOk or TestErr"`
Expected: FAIL with `ImportError: cannot import name 'ok'`

- [ ] **Step 3: Write minimal implementation**

Add to `logerr/functools.py` (after `or_result`):

```python
def ok[T, E](result: Result[T, E]) -> Option[T]:
    """Convert a Result into an Option, discarding any error.

    Args:
        result: The Result to convert.

    Returns:
        Some(value) if Ok, otherwise Nothing.

    Examples:
        >>> from logerr import Ok, Err
        >>> ok(Ok(42))
        Some(42)
        >>> ok(Err("boom"))
        Nothing('Empty option')
    """
    if result.is_ok():
        return Some(result.unwrap())
    return Nothing.empty()


def err[T, E](result: Result[T, E]) -> Option[E]:
    """Convert a Result into an Option of its error, discarding any value.

    Args:
        result: The Result to convert.

    Returns:
        Some(error) if Err, otherwise Nothing.

    Examples:
        >>> from logerr import Ok, Err
        >>> err(Err("boom"))
        Some('boom')
        >>> err(Ok(42))
        Nothing('Empty option')
    """
    if result.is_err():
        return Some(result.unwrap_err())
    return Nothing.empty()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_functools.py -v`
Expected: 30 passed

- [ ] **Step 5: Run quality checks**

Run: `pixi run -e dev quality`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add logerr/functools.py tests/unit/test_functools.py
git commit -m "Add ok/err Result-to-Option combinators"
```

---

### Task 5: `.zip()`/`.flatten()`/`.and_()`/`.or_()` methods and `__iter__` on Option

**Files:**
- Modify: `logerr/option.py` (add abstract methods to `Option` ABC around line 294, after `ok_or_else`; add concrete implementations to `Some` around line 405, after its `ok_or_else`; add concrete implementations to `Nothing` around line 654, after its `ok_or_else`)
- Modify: `tests/unit/test_option.py`

**Interfaces:**
- Consumes: `zip_option`, `flatten_option`, `and_option`, `or_option` from `logerr.functools` (Tasks 1-3).
- Produces: `Option.zip()`, `Option.flatten()`, `Option.and_()`, `Option.or_()`, `Option.__iter__()` — instance methods on `Some`/`Nothing`. Used by Task 7's docs updates. `__iter__` (yielding the value 0 or 1 times) means Python's own `zip()`/`itertools` functions already work correctly on `Option` values directly — no bespoke polymorphic wrapper needed in `logerr.functools` (see that module's docstring, Task 1).

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_option.py` (find the `TestSome`/`TestNothing` classes and add a new test class near the end of the file, matching the file's existing class-per-topic layout):

```python
class TestOptionCombinatorMethods:
    """Test that zip/flatten/and_/or_ methods delegate to logerr.functools."""

    def test_some_zip_some(self):
        result = Some(1).zip(Some("a"))
        assert result.is_some()
        assert result.unwrap() == (1, "a")

    def test_some_zip_nothing(self):
        result = Some(1).zip(Nothing.empty())
        assert result.is_nothing()

    def test_nothing_zip(self):
        result = Nothing.empty().zip(Some(1))
        assert result.is_nothing()

    def test_some_flatten(self):
        result = Some(Some(42)).flatten()
        assert result.is_some()
        assert result.unwrap() == 42

    def test_nothing_flatten(self):
        result = Nothing.empty().flatten()
        assert result.is_nothing()

    def test_some_and(self):
        result = Some(1).and_(Some("a"))
        assert result.is_some()
        assert result.unwrap() == "a"

    def test_nothing_and(self):
        result = Nothing.empty().and_(Some("a"))
        assert result.is_nothing()

    def test_some_or(self):
        result = Some(1).or_(Some(2))
        assert result.is_some()
        assert result.unwrap() == 1

    def test_nothing_or(self):
        result = Nothing.empty().or_(Some(2))
        assert result.is_some()
        assert result.unwrap() == 2

    def test_some_iter(self):
        assert list(Some(42)) == [42]

    def test_nothing_iter(self):
        assert list(Nothing.empty()) == []

    def test_builtin_zip_works_via_iter(self):
        """Once Option is iterable, Python's own zip() works directly -
        no bespoke logerr zip wrapper needed."""
        assert list(zip(Some(1), Some("a"))) == [(1, "a")]
        assert list(zip(Nothing.empty(), Some("a"))) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_option.py -v -k TestOptionCombinatorMethods`
Expected: FAIL with `AttributeError: 'Some' object has no attribute 'zip'`

- [ ] **Step 3: Write minimal implementation**

In `logerr/option.py`, change the import line:
```python
from collections.abc import Callable
```
to:
```python
from collections.abc import Callable, Iterator
```

In `logerr/option.py`, add to the `Option` ABC, immediately after the `ok_or_else` abstract method (ends around line 294 with `pass`):

```python
    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Iterate over the contained value, 0 or 1 times.

        Matches Rust's Option::iter() - lets Option compose with the
        standard iterator toolkit (zip, itertools, etc.) directly.

        Returns:
            An iterator yielding the value once if Some, or nothing if
            Nothing.

        Examples:
            >>> list(Some(42))
            [42]
            >>> list(Nothing.empty())
            []
        """
        pass

    @abstractmethod
    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        """Combine this Option with another into an Option of a tuple.

        Args:
            other: The Option to combine with.

        Returns:
            Some((value, other_value)) if both are Some, otherwise Nothing.

        Examples:
            >>> Some(1).zip(Some("a"))
            Some((1, 'a'))
            >>> Some(1).zip(Nothing.empty())  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass

    @abstractmethod
    def flatten(self: Option[Option[T]]) -> Option[T]:
        """Flatten a nested Option by one level.

        Returns:
            The inner Option if this is Some, otherwise Nothing.

        Examples:
            >>> Some(Some(42)).flatten()
            Some(42)
        """
        pass

    @abstractmethod
    def and_[U](self, other: Option[U]) -> Option[U]:
        """Return `other` if this is Some, otherwise Nothing.

        Args:
            other: The Option to return if this is Some.

        Returns:
            `other` if this is Some, otherwise Nothing.

        Examples:
            >>> Some(1).and_(Some("a"))
            Some('a')
            >>> Nothing.empty().and_(Some("a"))  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass

    @abstractmethod
    def or_(self, other: Option[T]) -> Option[T]:
        """Return this Option if Some, otherwise `other`.

        Args:
            other: The fallback Option if this is Nothing.

        Returns:
            This Option if Some, otherwise `other`.

        Examples:
            >>> Some(1).or_(Some(2))
            Some(1)
            >>> Nothing.empty().or_(Some(2))
            Some(2)
        """
        pass
```

In `logerr/option.py`, add to `Some`, immediately after its `ok_or_else` (around line 407):

```python
    def __iter__(self) -> Iterator[T]:
        yield self._value

    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        from .functools import zip_option

        return zip_option(self, other)

    def flatten(self: Some[Option[T]]) -> Option[T]:
        from .functools import flatten_option

        return flatten_option(self)

    def and_[U](self, other: Option[U]) -> Option[U]:
        from .functools import and_option

        return and_option(self, other)

    def or_(self, other: Option[T]) -> Option[T]:
        from .functools import or_option

        return or_option(self, other)
```

In `logerr/option.py`, add to `Nothing`, immediately after its `ok_or_else` (around line 656):

```python
    def __iter__(self) -> Iterator[T]:
        return iter(())

    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        from .functools import zip_option

        return zip_option(self, other)

    def flatten(self: Nothing[Option[T]]) -> Option[T]:
        from .functools import flatten_option

        return flatten_option(self)

    def and_[U](self, other: Option[U]) -> Option[U]:
        from .functools import and_option

        return and_option(self, other)

    def or_(self, other: Option[T]) -> Option[T]:
        from .functools import or_option

        return or_option(self, other)
```

Note: the import is inside each method (not at module top) because `logerr/functools.py` imports `from .option import ...` — a top-level import in `option.py` back into `functools.py` would be circular. This is a standard, cheap way to break the cycle (Python caches the module after first import, so the repeated `from .functools import ...` calls are not meaningfully slower after the first call).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_option.py -v -k TestOptionCombinatorMethods`
Expected: 12 passed

- [ ] **Step 5: Run the full test suite and quality checks**

Run: `pixi run -e dev check-all`
Expected: all pass (this also re-verifies `logerr/functools.py`'s own doctests referencing `Some`/`Nothing`/`Ok`/`Err` still pass, and catches any circular-import issue across the whole package)

- [ ] **Step 6: Commit**

```bash
git add logerr/option.py tests/unit/test_option.py
git commit -m "Add zip/flatten/and_/or_ methods and __iter__ to Option (Some/Nothing)"
```

---

### Task 6: `.zip()`/`.flatten()`/`.and_()`/`.or_()`/`.ok()`/`.err()` methods and `__iter__` on Result

**Files:**
- Modify: `logerr/result.py` (add abstract methods to `Result` ABC around line 233, after `or_else`; add concrete implementations to `Ok` around line 354, after its `or_else`; add concrete implementations to `Err` around line 559, after its `or_else`)
- Modify: `tests/unit/test_result.py`

**Interfaces:**
- Consumes: `zip_result`, `flatten_result`, `and_result`, `or_result`, `ok`, `err` from `logerr.functools` (Tasks 1-4).
- Produces: `Result.zip()`, `Result.flatten()`, `Result.and_()`, `Result.or_()`, `Result.ok()`, `Result.err()`, `Result.__iter__()` — instance methods on `Ok`/`Err`. Used by Task 7's docs updates. `__iter__` (yielding the Ok value 0 or 1 times, matching Rust's `Result::iter()` — the `Err` value is never yielded) means Python's own `zip()` already works correctly on `Result` values directly.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_result.py` (new test class near the end of the file, matching its existing class-per-topic layout):

```python
class TestResultCombinatorMethods:
    """Test that zip/flatten/and_/or_/ok/err methods delegate to logerr.functools."""

    def test_ok_zip_ok(self):
        result = Ok(1).zip(Ok("a"))
        assert result.is_ok()
        assert result.unwrap() == (1, "a")

    def test_ok_zip_err(self):
        result = Ok(1).zip(Err("boom"))
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_err_zip(self):
        result = Err("boom").zip(Ok(1))
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_ok_flatten(self):
        result = Ok(Ok(42)).flatten()
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_err_flatten(self):
        result = Err("boom").flatten()
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_ok_and(self):
        result = Ok(1).and_(Ok("a"))
        assert result.is_ok()
        assert result.unwrap() == "a"

    def test_err_and(self):
        result = Err("boom").and_(Ok("a"))
        assert result.is_err()
        assert result.unwrap_err() == "boom"

    def test_ok_or(self):
        result = Ok(1).or_(Err("fallback"))
        assert result.is_ok()
        assert result.unwrap() == 1

    def test_err_or(self):
        result = Err("primary").or_(Ok(2))
        assert result.is_ok()
        assert result.unwrap() == 2

    def test_ok_ok_method(self):
        result = Ok(42).ok()
        assert result.is_some()
        assert result.unwrap() == 42

    def test_err_ok_method(self):
        result = Err("boom").ok()
        assert result.is_nothing()

    def test_err_err_method(self):
        result = Err("boom").err()
        assert result.is_some()
        assert result.unwrap() == "boom"

    def test_ok_err_method(self):
        result = Ok(42).err()
        assert result.is_nothing()

    def test_ok_iter(self):
        assert list(Ok(42)) == [42]

    def test_err_iter(self):
        assert list(Err("boom")) == []

    def test_builtin_zip_works_via_iter(self):
        """Once Result is iterable, Python's own zip() works directly -
        no bespoke logerr zip wrapper needed."""
        assert list(zip(Ok(1), Ok("a"))) == [(1, "a")]
        assert list(zip(Err("boom"), Ok("a"))) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_result.py -v -k TestResultCombinatorMethods`
Expected: FAIL with `AttributeError: 'Ok' object has no attribute 'zip'`

- [ ] **Step 3: Write minimal implementation**

In `logerr/result.py`, change the import line:
```python
from collections.abc import Callable
```
to:
```python
from collections.abc import Callable, Iterator
```

In `logerr/result.py`, add to the `Result` ABC, immediately after the `or_else` abstract method (ends around line 233 with `pass`):

```python
    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Iterate over the Ok value, 0 or 1 times.

        Matches Rust's Result::iter() - the Err value is never yielded,
        only the Ok value if present. Lets Result compose with the
        standard iterator toolkit (zip, itertools, etc.) directly.

        Returns:
            An iterator yielding the value once if Ok, or nothing if Err.

        Examples:
            >>> list(Ok(42))
            [42]
            >>> list(Err("boom"))
            []
        """
        pass

    @abstractmethod
    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]:
        """Combine this Result with another into a Result of a tuple.

        Args:
            other: The Result to combine with.

        Returns:
            Ok((value, other_value)) if both are Ok, otherwise the first
            Err encountered (checking self before other).

        Examples:
            >>> Ok(1).zip(Ok("a"))
            Ok((1, 'a'))
            >>> Ok(1).zip(Err("boom"))  # doctest: +ELLIPSIS
            Err(...)
        """
        pass

    @abstractmethod
    def flatten(self: Result[Result[T, E], E]) -> Result[T, E]:
        """Flatten a nested Result by one level.

        Returns:
            The inner Result if this is Ok, otherwise this Err.

        Examples:
            >>> Ok(Ok(42)).flatten()
            Ok(42)
        """
        pass

    @abstractmethod
    def and_[U](self, other: Result[U, E]) -> Result[U, E]:
        """Return `other` if this is Ok, otherwise this Err.

        Args:
            other: The Result to return if this is Ok.

        Returns:
            `other` if this is Ok, otherwise this Err re-wrapped.

        Examples:
            >>> Ok(1).and_(Ok("a"))
            Ok('a')
            >>> Err("boom").and_(Ok("a"))  # doctest: +ELLIPSIS
            Err(...)
        """
        pass

    @abstractmethod
    def or_[F](self, other: Result[T, F]) -> Result[T, F]:
        """Return this Result if Ok, otherwise `other`.

        Args:
            other: The fallback Result if this is Err. May have a
                different error type than this Result.

        Returns:
            This Result's value re-wrapped if Ok, otherwise `other`.

        Examples:
            >>> Ok(1).or_(Err("fallback"))
            Ok(1)
            >>> Err("primary").or_(Ok(2))
            Ok(2)
        """
        pass

    @abstractmethod
    def ok(self) -> Option[T]:
        """Convert this Result into an Option, discarding any error.

        Returns:
            Some(value) if Ok, otherwise Nothing.

        Examples:
            >>> Ok(42).ok()
            Some(42)
            >>> Err("boom").ok()  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass

    @abstractmethod
    def err(self) -> Option[E]:
        """Convert this Result into an Option of its error.

        Returns:
            Some(error) if Err, otherwise Nothing.

        Examples:
            >>> Err("boom").err()
            Some('boom')
            >>> Ok(42).err()  # doctest: +ELLIPSIS
            Nothing(...)
        """
        pass
```

This requires importing `Option` in `logerr/result.py` for the `ok`/`err` return-type annotations. Since `logerr/option.py` imports `from .result import Err, Ok, Result` at module level already (a pre-existing one-way dependency: `option.py` depends on `result.py`, not the reverse), add the import under `TYPE_CHECKING` in `result.py` to avoid introducing a real circular import:

At the top of `logerr/result.py`, find:
```python
from typing import Any, TypeVar
```
Change to:
```python
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from .option import Option
```

In `logerr/result.py`, add to `Ok`, immediately after its `or_else` (around line 356):

```python
    def __iter__(self) -> Iterator[T]:
        yield self._value

    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]:
        from .functools import zip_result

        return zip_result(self, other)

    def flatten(self: Ok[Result[T, E], E]) -> Result[T, E]:
        from .functools import flatten_result

        return flatten_result(self)

    def and_[U](self, other: Result[U, E]) -> Result[U, E]:
        from .functools import and_result

        return and_result(self, other)

    def or_[F](self, other: Result[T, F]) -> Result[T, F]:
        from .functools import or_result

        return or_result(self, other)

    def ok(self) -> Option[T]:
        from .functools import ok as ok_fn

        return ok_fn(self)

    def err(self) -> Option[E]:
        from .functools import err as err_fn

        return err_fn(self)
```

In `logerr/result.py`, add to `Err`, immediately after its `or_else` (around line 561):

```python
    def __iter__(self) -> Iterator[T]:
        return iter(())

    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]:
        from .functools import zip_result

        return zip_result(self, other)

    def flatten(self: Err[Result[T, E], E]) -> Result[T, E]:
        from .functools import flatten_result

        return flatten_result(self)

    def and_[U](self, other: Result[U, E]) -> Result[U, E]:
        from .functools import and_result

        return and_result(self, other)

    def or_[F](self, other: Result[T, F]) -> Result[T, F]:
        from .functools import or_result

        return or_result(self, other)

    def ok(self) -> Option[T]:
        from .functools import ok as ok_fn

        return ok_fn(self)

    def err(self) -> Option[E]:
        from .functools import err as err_fn

        return err_fn(self)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_result.py -v -k TestResultCombinatorMethods`
Expected: 16 passed

- [ ] **Step 5: Run the full test suite and quality checks**

Run: `pixi run -e dev check-all`
Expected: all pass. Pay particular attention to mypy here — this task introduces `TYPE_CHECKING`-guarded imports and several `self: SpecificType[...]` narrowed-self annotations on `flatten`; if mypy complains about the narrowed `self` type, check that the annotation exactly matches the pattern used (`self: Some[Option[T]]`, `self: Ok[Result[T, E], E]`, etc.) rather than the class's own generic `self`.

- [ ] **Step 6: Commit**

```bash
git add logerr/result.py tests/unit/test_result.py
git commit -m "Add zip/flatten/and_/or_/ok/err methods and __iter__ to Result (Ok/Err)"
```

---

### Task 7: Type stubs, docs, and CHANGELOG

**Files:**
- Modify: `logerr/functools.pyi` (create)
- Modify: `logerr/option.pyi`
- Modify: `logerr/result.pyi`
- Modify: `pyproject.toml` (package-data already includes `logerr = ["*.pyi", "py.typed"]` — verify the new `.pyi` is picked up, no change needed if so)
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/guide/option-types.md`
- Modify: `docs/guide/result-types.md`
- Modify: `docs/api/utilities.md` mkdocs nav — actually add a new `docs/api/functools.md` and register it in `mkdocs.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: nothing further (terminal task).

- [ ] **Step 1: Create `logerr/functools.pyi`**

```python
"""Type stubs for logerr.functools module."""

from __future__ import annotations

from .option import Option
from .result import Result

def zip_option[T, U](a: Option[T], b: Option[U]) -> Option[tuple[T, U]]:
    """Combine two Options into an Option of a tuple."""
    ...

def zip_result[T, U, E](a: Result[T, E], b: Result[U, E]) -> Result[tuple[T, U], E]:
    """Combine two Results into a Result of a tuple."""
    ...

def flatten_option[T](nested: Option[Option[T]]) -> Option[T]:
    """Flatten a nested Option by one level."""
    ...

def flatten_result[T, E](nested: Result[Result[T, E], E]) -> Result[T, E]:
    """Flatten a nested Result by one level."""
    ...

def and_option[T, U](opt: Option[T], other: Option[U]) -> Option[U]:
    """Return other if opt is Some, otherwise Nothing."""
    ...

def and_result[T, U, E](res: Result[T, E], other: Result[U, E]) -> Result[U, E]:
    """Return other if res is Ok, otherwise the original Err."""
    ...

def or_option[T](opt: Option[T], other: Option[T]) -> Option[T]:
    """Return opt if Some, otherwise other."""
    ...

def or_result[T, E, F](res: Result[T, E], other: Result[T, F]) -> Result[T, F]:
    """Return res if Ok, otherwise other."""
    ...

def ok[T, E](result: Result[T, E]) -> Option[T]:
    """Convert a Result into an Option, discarding any error."""
    ...

def err[T, E](result: Result[T, E]) -> Option[E]:
    """Convert a Result into an Option of its error."""
    ...
```

- [ ] **Step 2: Update `logerr/option.pyi`**

Change:
```python
from collections.abc import Callable
```
to:
```python
from collections.abc import Callable, Iterator
```

Find the `Option` ABC's `ok_or_else` stub declaration and add immediately after it:

```python
    @abstractmethod
    def __iter__(self) -> Iterator[T]: ...
    @abstractmethod
    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]: ...
    @abstractmethod
    def flatten(self: Option[Option[T]]) -> Option[T]: ...
    @abstractmethod
    def and_[U](self, other: Option[U]) -> Option[U]: ...
    @abstractmethod
    def or_(self, other: Option[T]) -> Option[T]: ...
```

Find `Some`'s `ok_or_else` stub and add immediately after it:

```python
    def __iter__(self) -> Iterator[T]: ...
    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]: ...
    def flatten(self: Some[Option[T]]) -> Option[T]: ...
    def and_[U](self, other: Option[U]) -> Option[U]: ...
    def or_(self, other: Option[T]) -> Option[T]: ...
```

Find `Nothing`'s `ok_or_else` stub and add immediately after it:

```python
    def __iter__(self) -> Iterator[T]: ...
    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]: ...
    def flatten(self: Nothing[Option[T]]) -> Option[T]: ...
    def and_[U](self, other: Option[U]) -> Option[U]: ...
    def or_(self, other: Option[T]) -> Option[T]: ...
```

- [ ] **Step 3: Update `logerr/result.pyi`**

Change:
```python
from collections.abc import Callable
```
to:
```python
from collections.abc import Callable, Iterator
```

Find the `Result` ABC's `or_else` stub declaration and add immediately after it:

```python
    @abstractmethod
    def __iter__(self) -> Iterator[T]: ...
    @abstractmethod
    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]: ...
    @abstractmethod
    def flatten(self: Result[Result[T, E], E]) -> Result[T, E]: ...
    @abstractmethod
    def and_[U](self, other: Result[U, E]) -> Result[U, E]: ...
    @abstractmethod
    def or_[F](self, other: Result[T, F]) -> Result[T, F]: ...
    @abstractmethod
    def ok(self) -> Option[T]: ...
    @abstractmethod
    def err(self) -> Option[E]: ...
```

Add `from .option import Option` near the top of `result.pyi` if not already present (check first - `.pyi` files don't need `TYPE_CHECKING` guards since they're never executed).

Find `Ok`'s `or_else` stub and add immediately after it:

```python
    def __iter__(self) -> Iterator[T]: ...
    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]: ...
    def flatten(self: Ok[Result[T, E], E]) -> Result[T, E]: ...
    def and_[U](self, other: Result[U, E]) -> Result[U, E]: ...
    def or_[F](self, other: Result[T, F]) -> Result[T, F]: ...
    def ok(self) -> Option[T]: ...
    def err(self) -> Option[E]: ...
```

Find `Err`'s `or_else` stub and add immediately after it:

```python
    def __iter__(self) -> Iterator[T]: ...
    def zip[U](self, other: Result[U, E]) -> Result[tuple[T, U], E]: ...
    def flatten(self: Err[Result[T, E], E]) -> Result[T, E]: ...
    def and_[U](self, other: Result[U, E]) -> Result[U, E]: ...
    def or_[F](self, other: Result[T, F]) -> Result[T, F]: ...
    def ok(self) -> Option[T]: ...
    def err(self) -> Option[E]: ...
```

- [ ] **Step 4: Verify mypy is still clean with the new stubs**

Run: `rm -rf .mypy_cache && pixi run -e dev quality typecheck`
Expected: `Success: no issues found in 14 source files` (was 13 before this plan; +1 for the new `logerr.functools` module — mypy resolves `functools.py`/`functools.pyi` as a single module, using the `.pyi` in preference to the `.py`, not counting both separately)

- [ ] **Step 5: Add API reference page**

Create `docs/api/functools.md`:

```markdown
# Functools API Reference

Functional combinators for Option/Result - zip, flatten, and_, or_, ok, err.

::: logerr.functools
```

In `mkdocs.yml`, find:
```yaml
  - API Reference:
    - Result: api/result.md
    - Option: api/option.md
    - Configuration: api/config.md
    - Utilities: api/utilities.md
```
Change to:
```yaml
  - API Reference:
    - Result: api/result.md
    - Option: api/option.md
    - Configuration: api/config.md
    - Utilities: api/utilities.md
    - Functools: api/functools.md
```

- [ ] **Step 6: Verify docs build**

Run: `pixi run docs build`
Expected: `✅ Documentation built successfully!`

- [ ] **Step 7: Update `docs/guide/option-types.md`**

Find the `### or_else()` - Alternative Values section (near the end of the "Transforming Options" heading group) and add a new subsection immediately after it:

```markdown
### `zip()`, `flatten()`, `and_()`, `or_()` - Additional Combinators

```python
from logerr import Some, Nothing

# zip() - combine two Options into a tuple
Some(1).zip(Some("a"))          # Some((1, "a"))
Some(1).zip(Nothing.empty())    # Nothing

# flatten() - collapse a nested Option
Some(Some(42)).flatten()        # Some(42)

# and_() - return other if Some, otherwise Nothing
Some(1).and_(Some("a"))         # Some("a")
Nothing.empty().and_(Some("a")) # Nothing

# or_() - return self if Some, otherwise other
Some(1).or_(Some(2))            # Some(1)
Nothing.empty().or_(Some(2))    # Some(2)
```

`Option` is also iterable (yielding the value 0 or 1 times), so Python's
own `zip()`/`itertools` functions work on it directly - no logerr-specific
wrapper needed:

```python
list(Some(1))                          # [1]
list(Nothing.empty())                  # []
list(zip(Some(1), Some("a")))          # [(1, "a")]
```
```

- [ ] **Step 8: Update `docs/guide/result-types.md`**

Find the `### or_else()` - Error Recovery section and add a new subsection immediately after it:

```markdown
### `zip()`, `flatten()`, `and_()`, `or_()`, `ok()`, `err()` - Additional Combinators

```python
from logerr import Ok, Err

# zip() - combine two Results into a tuple (first Err wins)
Ok(1).zip(Ok("a"))              # Ok((1, "a"))
Ok(1).zip(Err("boom"))          # Err("boom")

# flatten() - collapse a nested Result
Ok(Ok(42)).flatten()            # Ok(42)

# and_() - return other if Ok, otherwise the original Err
Ok(1).and_(Ok("a"))             # Ok("a")
Err("boom").and_(Ok("a"))       # Err("boom")

# or_() - return self if Ok, otherwise other
Ok(1).or_(Err("fallback"))      # Ok(1)
Err("primary").or_(Ok(2))       # Ok(2)

# ok() / err() - convert to Option, discarding the other side
Ok(42).ok()                     # Some(42)
Err("boom").ok()                # Nothing
Err("boom").err()               # Some("boom")
Ok(42).err()                    # Nothing
```

`Result` is also iterable (yielding the Ok value 0 or 1 times, never the
Err value), so Python's own `zip()`/`itertools` functions work on it
directly:

```python
list(Ok(1))                            # [1]
list(Err("boom"))                      # []
list(zip(Ok(1), Ok("a")))              # [(1, "a")]
```
```

- [ ] **Step 9: Update `CLAUDE.md`**

Find the "### **Available Utility Functions**" table (the `logerr.utilities` table) and add a new subsection immediately after it:

```markdown
### **Combinator Methods on Option/Result**

`Some`/`Nothing`/`Ok`/`Err` also have `zip()`, `flatten()`, `and_()`, `or_()` methods (plus `ok()`/`err()` on `Result`), implemented as thin delegates to free functions in `logerr.functools` (`zip_option`, `zip_result`, `flatten_option`, `flatten_result`, `and_option`, `and_result`, `or_option`, `or_result`, `ok`, `err`). None of these invoke a callable, so - unlike `map`/`then`/`filter`/`or_else` - there's no exception-propagation question: a `Nothing`/`Err` input just propagates as-is.

`Option`/`Result` are also iterable now (`__iter__` yields the value 0 or 1 times - `Nothing`/`Err` yield nothing, `Some`/`Ok` yield their value once), matching Rust's own `Option::iter()`/`Result::iter()`. This means Python's own `zip()` and the standard `itertools` toolkit already work correctly on `Option`/`Result` values directly - there's deliberately no bespoke `logerr` `zip()` wrapper that could behave differently from the real one depending on what you pass it.
```

- [ ] **Step 10: Update `README.md`**

Find the "🌟 Features" bullet list and add one bullet after "Rust-like Types":

```markdown
- **🔗 Full Combinator Set**: `zip()`, `flatten()`, `and_()`, `or_()`, `ok()`, `err()` alongside the core `map`/`then`/`filter`
```

- [ ] **Step 11: Add CHANGELOG entry**

Add to `CHANGELOG.md` under `## [Unreleased]`, in the `### Added` section (create one if the current top entry is a different section):

```markdown
### Added

- `logerr.functools` - free-function combinators (`zip_option`, `zip_result`,
  `flatten_option`, `flatten_result`, `and_option`, `and_result`,
  `or_option`, `or_result`, `ok`, `err`), mirroring Rust's `Option`/`Result`
  API surface. `Option`/`Result` gained matching `zip()`/`flatten()`/
  `and_()`/`or_()` methods (`ok()`/`err()` on `Result` only) that delegate
  to these functions. None of the ten invoke a user-supplied callable, so
  none of them carry the exception-catch-vs-propagate question that
  `map`/`then`/`filter`/`or_else` do.
- `Option`/`Result` are now iterable (`__iter__` yields the value 0 or 1
  times, matching Rust's `Option::iter()`/`Result::iter()` - `Result`
  never yields the `Err` value). This means Python's own `zip()` and the
  standard `itertools` toolkit already work correctly on `Option`/`Result`
  directly, with no bespoke `logerr` `zip()` wrapper that could behave
  differently from the real one depending on what you pass it.
```

- [ ] **Step 12: Final full verification**

Run: `rm -rf .mypy_cache && pixi run -e dev check-all`
Expected: all green, coverage should be ~97%+ still (new code is fully covered by Tasks 1-6's tests)

- [ ] **Step 13: Commit**

```bash
git add logerr/functools.pyi logerr/option.pyi logerr/result.pyi docs/api/functools.md mkdocs.yml docs/guide/option-types.md docs/guide/result-types.md CLAUDE.md README.md CHANGELOG.md
git commit -m "Add type stubs and docs for logerr.functools combinators"
```

- [ ] **Step 14: Push**

```bash
git push origin main
```

---

## Self-Review Notes

- **Spec coverage:** all 10 functions (Task 1-4), all ~10 methods across `Some`/`Nothing`/`Ok`/`Err` (Task 5-6), `.pyi` stubs + docs + CHANGELOG (Task 7). `logerr.itertools`/`sequence`/`traverse` explicitly out of scope per spec - not covered here, by design.
- **Type consistency:** function names (`zip_option`, `zip_result`, `flatten_option`, `flatten_result`, `and_option`, `and_result`, `or_option`, `or_result`, `ok`, `err`) are identical across Tasks 1-4 (definition), Task 5-6 (method bodies calling them), and Task 7 (`.pyi` stubs) - verified by re-reading each reference while writing this plan.
- **Circular import handling:** `logerr/functools.py` imports from both `option.py` and `result.py` at module level (safe - neither of those import `functools.py`). The methods on `Option`/`Result` import `from .functools import ...` *inside each method body*, not at module top, specifically to avoid `option.py`/`result.py` importing `functools.py` at module level while `functools.py` imports them at module level (that would be the actual cycle). `result.py`'s `ok()`/`err()` methods needing the `Option` type for annotations use a `TYPE_CHECKING`-guarded import, not a runtime one, since `option.py` already imports `result.py` at module level today - a real runtime import the other direction would be the actual circular-import bug.
- **Mid-plan revision (before any task was executed):** original draft had `zip`/`flatten` as *polymorphic* free functions in `logerr.functools` (dispatching via `isinstance`/`match` on Option vs Result vs plain iterable, falling back to `builtins.zip`/`itertools.chain.from_iterable`). Removed after discussion — a `zip()` that behaves differently depending on what you hand it is surprising, and duplicates logic Python already provides for free once `Option`/`Result` are iterable. Replaced with `__iter__` on `Some`/`Nothing`/`Ok`/`Err` (folded into Tasks 5/6, since they already touch those classes) — Python's *actual* `zip()`/`itertools` now work correctly on `Option`/`Result` with zero `logerr`-specific code, and `zip_option`/`zip_result`/`.zip()` remain a clearly separate, differently-named operation (combine two Options/Results into one, not "iterate in lockstep"). A related but distinct request — zipping *collections* of Results into one Result of a list (`zip([Ok(0)], [Ok(1)]) -> Ok([(0, 1)])`, i.e. "traverse") — was identified as a different problem shape (operates across many values, not two) and confirmed deferred to the future `logerr.itertools` spec alongside `sequence`/`traverse`, not added here.
