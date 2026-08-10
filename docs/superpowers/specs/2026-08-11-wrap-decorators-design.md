# `wrap_result` / `wrap_option`: function-boundary exception-to-Result/Option decorators

## Context

Client code that mixes ordinary imperative code (context managers, multiple
statements) with Result-returning calls currently repeats this shape:

```python
try:
    with httpx.Client() as http_client:
        pulled_result = traverse_result(
            feature_refs,
            lambda ref: pull_feature(http_client, ref, settings.data_dir / "features"),
        )
except Exception as exc:
    return Err(exc)
if pulled_result.is_err():
    return Err(pulled_result.unwrap_err())
```

Two separate pieces of boilerplate:
1. A manual `try/except` converting any raised exception into `Err`.
2. Unwrapping an already-`Result` value (`pulled_result`) just to re-wrap it
   as `Err` - equivalent to `return pulled_result`, but written the long way.

A `with wrap_result:` statement was the first idea raised, but Python gives
context managers no way to intercept a `return` inside the `with` block and
redirect it to become the enclosing function's return value - `__exit__` can
only suppress/transform an exception, not capture a block's value as the
function's result. A **decorator** wrapping the whole function has no such
limitation, and the codebase already has this exact shape: `on_err`/
`on_err_type` in `logerr/recipes/retry.py` wrap a `Result`-returning
function via `functools.wraps`.

This spec adds `wrap_result`/`wrap_option` to core `logerr/utilities.py`
(no tenacity/pandas/pymongo dependency, same reasoning as every other
function already there).

**Design constraint from prior work:** the CHANGELOG documents a deliberate
move away from broad exception-catching in `map`/`then`/`filter`/`or_else` -
those used to silently convert *any* exception (including bugs like a typo
causing `AttributeError`) into `Nothing`/`Err`, masking real programming
errors as domain failures. Catching was deliberately narrowed to explicit,
named entry points: `Option.of`/`Result.of`, `from_predicate`, `execute()`.
`wrap_result`/`wrap_option` are exactly this kind of explicit entry point -
decorating a function is an opt-in, visible declaration that "exceptions
raised in this function become domain failures," which is different from
`map`/`then` catching invisibly mid-chain.

## Behavior

Both decorators are used bare, no required arguments (nothing to configure
given the "catch bare `Exception`" decision below):

```python
@wrap_result
def pull_all(settings, feature_refs) -> Result[list[Feature], Exception]:
    with httpx.Client() as http_client:
        return traverse_result(
            feature_refs,
            lambda ref: pull_feature(http_client, ref, settings.data_dir / "features"),
        )
```

Rules, checked in this order:
1. **Raises** -> caught (bare `Exception`, matching `Result.of`/`execute`)
   and converted to `Err.from_exception(exc)` / `Nothing.from_exception(exc)`
   (auto-logged the same way `Result.of` already logs, via `Err`'s/
   `Nothing`'s own constructor - no new logging path).
2. **Returns a `Result`/`Option` already** -> passed through unchanged. No
   re-wrapping, so no `unwrap_err`-then-`Err(...)` boilerplate at call
   sites that already produce a `Result`/`Option` internally.
3. **Returns a plain value** -> wrapped as `Ok(value)` / (`Some(value)` if
   not `None`, else `Nothing.from_none(...)`, matching `nullable()`'s
   existing None-handling so `wrap_option` doesn't invent a second
   None-handling convention).

`functools.wraps` preserves `__name__`/`__doc__`/signature, matching
`on_err`'s existing convention.

## Typing

```python
def wrap_result[T, E](
    func: Callable[..., T | Result[T, E]],
) -> Callable[..., Result[T, E]]:
```

The exception path always produces `Err.from_exception(exc)`, which is
`Err[Any, Exception]` - if the function's declared `E` isn't `Exception`,
this is the same "exception handling changes the error type" situation
`from_predicate` already has in `result.py` (handled there with a
`# type: ignore[return-value]` and an explanatory comment). `wrap_result`
follows that exact precedent rather than inventing a new typing approach.
`wrap_option[T]` is simpler (no error-type parameter to reconcile).

## Files touched

- Modified: `logerr/utilities.py` (+`wrap_result`, `+wrap_option`)
- Modified: `logerr/utilities.pyi` (+ stub signatures, matching the existing
  `@overload` style already used for `execute`/`nullable`/`validate` where
  applicable - these two don't need `@overload` since each has one fixed
  output type, unlike `execute`'s option/result branch)
- Modified: `tests/unit/test_utilities.py`:
  - `wrap_result`: raw-value success -> `Ok`; returns-`Result` pass-through
    (`Ok` and `Err` cases, confirming no double-wrap); raised exception ->
    `Err`; `functools.wraps` preserves `__name__`.
  - `wrap_option`: raw non-`None` -> `Some`; raw `None` -> `Nothing`;
    returns-`Option` pass-through (`Some` and `Nothing` cases); raised
    exception -> `Nothing`; `functools.wraps` preserves `__name__`.
- Modified: `CLAUDE.md` - add both to the `logerr.utilities` function table,
  with a short example mirroring the `pull_all` case above.
- Modified: `CHANGELOG.md` - `### Added` entry.

## Testing plan (TDD)

Write the `test_utilities.py` cases above first (they fully specify the
three-rule behavior), watch them fail against the not-yet-written
functions, then implement `wrap_result`/`wrap_option` to make them pass -
consistent with this repo's existing test-first expectation
(`superpowers:test-driven-development`).

## Non-goals

- No async function support (no real use case yet; add later if needed).
- No caller-configurable exception types (e.g. `@wrap_result(httpx.HTTPError)`)
  - bare `Exception` matches `Result.of`'s existing philosophy; narrower
    catching is a different, stricter design that wasn't chosen here.
- No changes to `map`/`then`/`filter`/`or_else` - those already propagate
  exceptions by design (see Context) and this spec doesn't revisit that.
- No context-manager variant (`with wrap_result():`) - ruled out in Context
  as unable to actually replace the `try/except` + `return` shape being
  targeted here.
