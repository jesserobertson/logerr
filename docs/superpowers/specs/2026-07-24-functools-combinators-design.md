# `logerr.functools`: Option/Result combinators

## Context

`logerr` already has `logerr.utilities` for safe-execution/validation helpers
(`execute`, `nullable`, `validate`, `chain`, etc.) - all "callable-wrapping"
patterns. This spec covers a different category: pure value combinators that
Rust's `Option`/`Result` have and logerr's currently don't (`zip`, `and`,
`or`, `ok`, `err`, `flatten`). None of these invoke user-supplied callables,
so they carry no exception-catch-vs-propagate design tension - there's
nothing to catch.

The docs review earlier in this session found a README example calling a
fictional `Option.zip()`. This spec fills that gap properly instead of just
deleting the broken example.

Deferred to a future spec: `logerr.itertools` for collection-level operations
(`sequence`, `traverse`) that fold a `list[Option[T]]`/`list[Result[T,E]]`
into `Option[list[T]]`/`Result[list[T],E]`. Different problem shape (operates
across many values, not two), not needed to unblock this round.

## Architecture

Free functions live in a new `logerr/functools.py` (mirrors stdlib
`functools` naming - these are transforms/combinators, not iteration
constructs). `Option`/`Result` subclasses (`Some`/`Nothing`, `Ok`/`Err`) gain
thin instance methods that delegate to these functions, for discoverability
and chaining ergonomics:

```python
# logerr/functools.py
def zip_option(a: Option[T], b: Option[U]) -> Option[tuple[T, U]]: ...

# logerr/option.py
class Some(Option[T]):
    def zip[U](self, other: Option[U]) -> Option[tuple[T, U]]:
        return zip_option(self, other)
```

No dependency on tenacity/pandas/pymongo, so `logerr.functools` lives in
core, same reasoning as this session's `recipes.utilities` -> core
`utilities` consolidation.

## Functions and semantics

All ten operate purely on values already produced - no callable is invoked,
so no exception can arise from *these* functions' own logic (a
`flatten_option` call site that violates the `Option[Option[T]]` type
contract at runtime is a caller bug; let it surface as a natural
`AttributeError`/`TypeError` rather than adding defensive type-checking -
consistent with "trust internal callers" elsewhere in this codebase).

| Function | Signature | Semantics | Rust origin |
|---|---|---|---|
| `zip_option` | `(Option[T], Option[U]) -> Option[tuple[T,U]]` | `Some`+`Some` -> `Some(tuple)`; either `Nothing` -> `Nothing` | `Option::zip` |
| `zip_result` | `(Result[T,E], Result[U,E]) -> Result[tuple[T,U],E]` | `Ok`+`Ok` -> `Ok(tuple)`; first `Err` wins | none (logerr addition, by request) |
| `flatten_option` | `Option[Option[T]] -> Option[T]` | Unwraps one level of nesting | `Option::flatten` |
| `flatten_result` | `Result[Result[T,E],E] -> Result[T,E]` | Unwraps one level of nesting | none (logerr addition, for symmetry) |
| `and_option` | `(Option[T], Option[U]) -> Option[U]` | `Some` -> returns `other`; `Nothing` -> `Nothing` | `Option::and` |
| `and_result` | `(Result[T,E], Result[U,E]) -> Result[U,E]` | `Ok` -> returns `other`; `Err` -> self unchanged | `Result::and` |
| `or_option` | `(Option[T], Option[T]) -> Option[T]` | `Some` -> self; `Nothing` -> returns `other` | `Option::or` |
| `or_result` | `(Result[T,E], Result[T,F]) -> Result[T,F]` | `Ok` -> self; `Err` -> returns `other` | `Result::or` |
| `ok` | `Result[T,E] -> Option[T]` | `Ok(v)` -> `Some(v)`; `Err(_)` -> `Nothing` | `Result::ok` |
| `err` | `Result[T,E] -> Option[E]` | `Err(e)` -> `Some(e)`; `Ok(_)` -> `Nothing` | `Result::err` |

Method names: `zip`, `flatten`, `and_`, `or_`, `ok`, `err` (trailing
underscore on `and_`/`or_` since `and`/`or` are Python keywords - same
convention Rust itself would use if it needed one, and matches this
codebase's existing `filter`/`map` naming style otherwise).

## Files touched

- New: `logerr/functools.py`, `logerr/functools.pyi`
- New: `tests/unit/test_functools.py` (function-level tests)
- Modified: `logerr/option.py` (+method on `Option` ABC, `Some`, `Nothing`),
  `logerr/option.pyi`
- Modified: `logerr/result.py` (+method on `Result` ABC, `Ok`, `Err`),
  `logerr/result.pyi`
- Modified: `tests/unit/test_option.py`, `tests/unit/test_result.py`
  (method-delegation tests - thin, just confirm the method calls through)
- Modified: `CLAUDE.md`, `README.md`, relevant `docs/guide/*.md` - mention
  the new methods where the existing option-types.md/result-types.md guides
  already walk through the method surface
- `CHANGELOG.md`: `### Added` entry

## Testing plan (TDD)

Each of the 10 functions gets direct tests in `test_functools.py` covering:
present/present, present/absent, absent/present, absent/absent (for the
2-argument ones), plus the `Ok`/`Err` variants. `ok`/`err`/`flatten_*` get
their two/three cases each.

Each of the ~10 new methods gets one thin test confirming it delegates
correctly (not re-testing the full matrix - that's the function tests'
job).

## Non-goals

- No `zip_with(other, f)` (Rust nightly-only, combines via function instead
  of tuple) - not requested, adds a callable-execution edge case back into
  an otherwise callable-free feature set.
- No changes to `map`/`then`/`filter`/`or_else`/`map_err` (already handled
  this session).
- No `logerr.itertools` (`sequence`/`traverse`) - deferred, see Context.
