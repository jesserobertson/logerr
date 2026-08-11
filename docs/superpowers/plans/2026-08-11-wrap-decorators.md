# wrap_result / wrap_option Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `wrap_result`/`wrap_option` decorators to `logerr.utilities` so a whole function body (not just a single callable) gets exception-to-`Err`/`Nothing` conversion, and a returned `Result`/`Option` passes through unchanged instead of needing `unwrap_err()`-then-rewrap.

**Architecture:** Two bare decorators (no required arguments) added to the existing `logerr/utilities.py` module, following the exact `functools.wraps`-based wrapper shape already used by `on_err`/`on_err_type` in `logerr/recipes/retry.py`. Each decorator's `wrapper` does: call the function inside `try/except Exception`; on exception, return `Err.from_exception(exc)` / `Nothing.from_exception(exc)`; on success, pass a `Result`/`Option` return value through unchanged, otherwise wrap a raw value (`Ok(value)`, or `Some(value)`/`Nothing.from_none(...)` for `None`).

**Tech Stack:** Python 3.13 (PEP 695 generics, `def f[T, E](...)` syntax already used throughout this codebase), pytest, mypy, ruff. No new dependencies.

## Global Constraints

- Core module only — `logerr/utilities.py` has no tenacity/pandas/pymongo dependency; neither decorator may import from `logerr.recipes`.
- Catch bare `Exception` only (no caller-configurable exception filter) — matches `Result.of`/`execute`'s existing philosophy per the spec.
- No async support — sync functions only.
- Must pass `pixi run -e dev check-all` (tests + mypy + ruff) before any commit that isn't itself a WIP intermediate — but per this repo's CLAUDE.md, only the *final* commit of the feature must pass; TDD steps below run `pytest` directly per-file, not the full `check-all`, until the last task.
- Follow this repo's existing `.py`/`.pyi` stub-file split: runtime code has no type-checking-only complexity: the `.pyi` carries the full typed signature, the `.py` implementation stays simple.

---

## File Structure

- Modify: `logerr/utilities.py` — add `wrap_result`, `wrap_option` functions, right after `try_chain` (end of file), keeping the existing top-of-file import block.
- Modify: `logerr/utilities.pyi` — add matching stub signatures.
- Modify: `tests/unit/test_utilities.py` — add `TestWrapResult`, `TestWrapOption` classes, following the existing `TestExecute`/`TestNullable` class-per-function pattern in that file.
- Modify: `CLAUDE.md` — add two rows to the `logerr.utilities` function table (line ~343-344), plus a short prose note (mirroring the "Combinator Methods" prose block style) explaining the pass-through/raw-wrap/exception-catch rules and pointing at the motivating example.
- Modify: `CHANGELOG.md` — add a `### Added` entry under `## [Unreleased]`.

No new files. Both functions are small enough to live in the existing `utilities.py` alongside their siblings, consistent with "follow established patterns" — this repo already groups all core function-wrapping utilities in one file.

---

### Task 1: `wrap_result` decorator

**Files:**
- Modify: `logerr/utilities.py`
- Modify: `logerr/utilities.pyi`
- Test: `tests/unit/test_utilities.py`

**Interfaces:**
- Consumes: `Result`, `Ok`, `Err` (already imported at top of `utilities.py` — `from .result import Err, Ok, Result`), `functools` (needs a new `import functools` at the top of `utilities.py`, alongside the existing `import sys`).
- Produces: `wrap_result(func: Callable[..., T | Result[T, E]]) -> Callable[..., Result[T, E]]`, importable as `from logerr.utilities import wrap_result`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_utilities.py`, after the existing `TestChain` class (end of file):

```python
class TestWrapResult:
    """Test the wrap_result decorator."""

    def test_wrap_result_raw_value_becomes_ok(self):
        """A plain return value is wrapped as Ok."""

        @wrap_result
        def f():
            return 42

        result = f()
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_wrap_result_passes_through_ok(self):
        """A returned Ok is passed through unchanged, not re-wrapped."""

        @wrap_result
        def f():
            return Ok(42)

        result = f()
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_wrap_result_passes_through_err_without_rewrap(self):
        """A returned Err is passed through unchanged - no unwrap_err/rewrap needed."""
        inner_err = Err.from_value("boom")

        @wrap_result
        def f():
            return inner_err

        result = f()
        assert result.is_err()
        assert result is inner_err

    def test_wrap_result_exception_becomes_err(self):
        """A raised exception is caught and converted to Err."""

        @wrap_result
        def f():
            raise ValueError("bad input")

        result = f()
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ValueError)
        assert str(result.unwrap_err()) == "bad input"

    def test_wrap_result_preserves_function_name(self):
        """functools.wraps preserves __name__, matching on_err's convention."""

        @wrap_result
        def my_named_function():
            return 1

        assert my_named_function.__name__ == "my_named_function"

    def test_wrap_result_passes_args_and_kwargs(self):
        """Decorated function still receives its original arguments."""

        @wrap_result
        def add(a, b, *, c=0):
            return a + b + c

        result = add(1, 2, c=3)
        assert result.is_ok()
        assert result.unwrap() == 6
```

Add `wrap_result` to the existing `from logerr.utilities import (...)` block at the top of the file, and add `from logerr import Err, Ok` (or extend the existing `from logerr import Nothing, Some` line to `from logerr import Err, Nothing, Ok, Some`) — check the current import line first since `Ok`/`Err` aren't currently imported in this test file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_utilities.py -k TestWrapResult -v`
Expected: FAIL with `ImportError: cannot import name 'wrap_result'`

- [ ] **Step 3: Implement `wrap_result`**

Add `import functools` near the top of `logerr/utilities.py` (alongside the existing `import sys`). Then append to the end of `logerr/utilities.py`, after `try_chain`:

```python
def wrap_result[T, E](
    func: Callable[..., T | Result[T, E]],
) -> Callable[..., Result[T, E]]:
    """Decorate a function so exceptions and return values both become a Result.

    Eliminates the common try/except-then-return-Err boilerplate around a
    function body that mixes ordinary code with Result-returning calls:
    - Returns a Result already? Passed through unchanged - no unwrap_err()
      then re-wrap needed.
    - Returns a plain value? Wrapped as Ok(value).
    - Raises? Caught and converted to Err(exception), auto-logged the same
      way Result.of() already logs (via Err's own constructor).

    Args:
        func: The function to decorate. May return T or Result[T, E].

    Returns:
        A wrapped function that always returns a Result[T, E].

    Examples:
        >>> @wrap_result
        ... def parse(text: str) -> int:
        ...     return int(text)
        >>> parse("42").unwrap()
        42
        >>> parse("nope").is_err()
        True
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, E]:
        try:
            outcome = func(*args, **kwargs)
        except Exception as e:
            # Type: ignore because exception handling changes the error type,
            # but this is expected behavior (see Result.from_predicate).
            return Err.from_exception(e)  # type: ignore[return-value]
        if isinstance(outcome, Result):
            return outcome
        return Ok(outcome)

    return wrapper
```

Add the matching stub to `logerr/utilities.pyi`, after the `try_chain` stub:

```python
def wrap_result[T, E](
    func: Callable[..., T | Result[T, E]],
) -> Callable[..., Result[T, E]]:
    """Decorate a function so exceptions and return values both become a Result."""
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_utilities.py -k TestWrapResult -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add logerr/utilities.py logerr/utilities.pyi tests/unit/test_utilities.py
git commit -m "$(cat <<'EOF'
Add wrap_result decorator to logerr.utilities

Lets a function body mix ordinary code with Result-returning calls
without manual try/except-to-Err boilerplate, and without needing
unwrap_err()-then-rewrap when a call already returns a Result.
EOF
)"
```

---

### Task 2: `wrap_option` decorator

**Files:**
- Modify: `logerr/utilities.py`
- Modify: `logerr/utilities.pyi`
- Test: `tests/unit/test_utilities.py`

**Interfaces:**
- Consumes: `Option`, `Some`, `Nothing` (already imported at top of `utilities.py` — `from .option import Nothing, Option, Some`).
- Produces: `wrap_option(func: Callable[..., T | Option[T]]) -> Callable[..., Option[T]]`, importable as `from logerr.utilities import wrap_option`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_utilities.py`, after `TestWrapResult`:

```python
class TestWrapOption:
    """Test the wrap_option decorator."""

    def test_wrap_option_raw_value_becomes_some(self):
        """A plain non-None return value is wrapped as Some."""

        @wrap_option
        def f():
            return 42

        result = f()
        assert result.is_some()
        assert result.unwrap() == 42

    def test_wrap_option_none_becomes_nothing(self):
        """A plain None return value becomes Nothing."""

        @wrap_option
        def f():
            return None

        result = f()
        assert result.is_nothing()

    def test_wrap_option_passes_through_some(self):
        """A returned Some is passed through unchanged, not re-wrapped."""

        @wrap_option
        def f():
            return Some(42)

        result = f()
        assert result.is_some()
        assert result.unwrap() == 42

    def test_wrap_option_passes_through_nothing(self):
        """A returned Nothing is passed through unchanged."""
        inner_nothing = Nothing.from_none("no value")

        @wrap_option
        def f():
            return inner_nothing

        result = f()
        assert result.is_nothing()
        assert result is inner_nothing

    def test_wrap_option_exception_becomes_nothing(self):
        """A raised exception is caught and converted to Nothing."""

        @wrap_option
        def f():
            raise ValueError("bad input")

        result = f()
        assert result.is_nothing()

    def test_wrap_option_preserves_function_name(self):
        """functools.wraps preserves __name__, matching wrap_result's convention."""

        @wrap_option
        def my_named_function():
            return 1

        assert my_named_function.__name__ == "my_named_function"

    def test_wrap_option_passes_args_and_kwargs(self):
        """Decorated function still receives its original arguments."""

        @wrap_option
        def add(a, b, *, c=0):
            return a + b + c

        result = add(1, 2, c=3)
        assert result.is_some()
        assert result.unwrap() == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run -e dev pytest tests/unit/test_utilities.py -k TestWrapOption -v`
Expected: FAIL with `ImportError: cannot import name 'wrap_option'`

- [ ] **Step 3: Implement `wrap_option`**

Append to the end of `logerr/utilities.py`, after `wrap_result`:

```python
def wrap_option[T](func: Callable[..., T | Option[T]]) -> Callable[..., Option[T]]:
    """Decorate a function so exceptions and return values both become an Option.

    Mirrors wrap_result() for the Option case:
    - Returns an Option already? Passed through unchanged.
    - Returns a non-None plain value? Wrapped as Some(value).
    - Returns None? Converted to Nothing (matching nullable()'s existing
      None-handling, so there's a single None-handling convention).
    - Raises? Caught and converted to Nothing, auto-logged via Nothing's
      own constructor.

    Args:
        func: The function to decorate. May return T, None, or Option[T].

    Returns:
        A wrapped function that always returns an Option[T].

    Examples:
        >>> @wrap_option
        ... def find(items: list[int], target: int) -> int | None:
        ...     return next((x for x in items if x == target), None)
        >>> find([1, 2, 3], 2).unwrap()
        2
        >>> find([1, 2, 3], 9).is_nothing()
        True
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Option[T]:
        try:
            outcome = func(*args, **kwargs)
        except Exception as e:
            return Nothing.from_exception(e)
        if isinstance(outcome, Option):
            return outcome
        if outcome is None:
            return Nothing.from_none("Function returned None")
        return Some(outcome)

    return wrapper
```

Add the matching stub to `logerr/utilities.pyi`, after the `wrap_result` stub:

```python
def wrap_option[T](func: Callable[..., T | Option[T]]) -> Callable[..., Option[T]]:
    """Decorate a function so exceptions and return values both become an Option."""
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run -e dev pytest tests/unit/test_utilities.py -k TestWrapOption -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add logerr/utilities.py logerr/utilities.pyi tests/unit/test_utilities.py
git commit -m "$(cat <<'EOF'
Add wrap_option decorator to logerr.utilities

Mirrors wrap_result() for Option: raw values become Some, None
becomes Nothing, an already-Option return passes through unchanged,
and raised exceptions become Nothing.
EOF
)"
```

---

### Task 3: Docs, changelog, and full quality gate

**Files:**
- Modify: `CLAUDE.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `wrap_result`, `wrap_option` (from Tasks 1-2, already implemented and tested).
- Produces: nothing new — documentation only.

- [ ] **Step 1: Update the utilities table in CLAUDE.md**

In `CLAUDE.md`, find the table under `### **Available Utility Functions**` (the block containing `| \`try_chain()\` | Try callables in order, return first success | Fallback strategies |`). Add two rows immediately after that line:

```markdown
| `wrap_result()` | Decorate a function so exceptions -> Err, returned Result passes through, plain value -> Ok | Mixing ordinary code (context managers, multiple statements) with Result-returning calls without manual try/except |
| `wrap_option()` | Decorate a function so exceptions -> Nothing, returned Option passes through, plain value -> Some/None -> Nothing | Same as wrap_result(), for Option-returning functions |
```

Then add one short paragraph after the table (before the `### **Combinator Methods on Option/Result**` heading), matching the prose style already used for the "Combinator Methods" section:

```markdown
`wrap_result()`/`wrap_option()` solve a different problem than `execute()`:
`execute()` wraps a single callable's *return value*; `wrap_result()`/
`wrap_option()` decorate a whole function so its *body* can mix ordinary
imperative code (context managers, multiple statements) with
Result/Option-returning calls, with no manual `try/except` and no
`unwrap_err()`-then-rewrap when a call already returns a `Result`/`Option`:

\```python
@wrap_result
def pull_all(settings, feature_refs) -> Result[list[Feature], Exception]:
    with httpx.Client() as http_client:
        return traverse_result(
            feature_refs,
            lambda ref: pull_feature(http_client, ref, settings.data_dir / "features"),
        )
\```
```

(Use real triple-backtick fences, not escaped, when writing this into the file — shown escaped here only to nest inside this plan's own code block.)

- [ ] **Step 2: Add a CHANGELOG entry**

In `CHANGELOG.md`, under `## [Unreleased]` (currently empty, right above `## [0.2.0] - 2026-07-25`), add:

```markdown
### Added

- `wrap_result()`/`wrap_option()` in `logerr.utilities`: decorate a whole
  function so exceptions become `Err`/`Nothing`, a returned `Result`/
  `Option` passes through unchanged, and a plain return value is wrapped
  as `Ok`/`Some` (`None` -> `Nothing` for `wrap_option`). Eliminates
  manual `try/except`-to-`Err` boilerplate and the
  `unwrap_err()`-then-rewrap pattern around functions that mix ordinary
  code with Result/Option-returning calls.
```

- [ ] **Step 3: Run the full quality gate**

Run: `pixi run -e dev check-all`
Expected: all tests pass (including the new doctests in `wrap_result`/`wrap_option`'s docstrings, picked up by `--doctest-modules logerr`), mypy reports no errors, ruff lint and format checks pass.

If mypy flags the `T | Result[T, E]` / `T | Option[T]` union signatures (e.g. because `T` can't be disambiguated from `Result[T, E]` when `T` itself could be a `Result`), fix by keeping the runtime `isinstance` check as the sole source of truth and adjust only the stub if mypy's inference genuinely fails - do not weaken the runtime behavior to satisfy the type checker.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md CHANGELOG.md
git commit -m "$(cat <<'EOF'
Document wrap_result/wrap_option in CLAUDE.md and CHANGELOG

EOF
)"
```

---

## Self-Review Notes

**Spec coverage:** Behavior rules 1-3 (raise -> Err/Nothing, Result/Option passthrough, raw value -> Ok/Some) are each covered by dedicated tests in Task 1 and Task 2. `functools.wraps` requirement covered by the `preserves_function_name` tests. Typing precedent (`from_predicate`'s `# type: ignore[return-value]` pattern) is followed literally in Task 1 Step 3. Placement in core `utilities.py` (not `recipes/`) is the File Structure decision. Non-goals (async, configurable exception filter, context-manager variant) require no tasks since they're explicitly not being built.

**Placeholder scan:** No TBD/TODO; every step has literal code.

**Type consistency:** `wrap_result`/`wrap_option` names and signatures match exactly between the `.py` implementation (Tasks 1-2 Step 3) and `.pyi` stub in the same steps, and match the `CLAUDE.md` table/example added in Task 3.
