# `logerr.itertools` Design

## Context

`logerr.functools` (added earlier) covers pairwise combinators (`zip_option`,
`flatten_option`, `and_option`, `or_option`, and their `_result` counterparts,
plus `ok`/`err`) and made `Option`/`Result` iterable, so the standard
`itertools` toolkit (`chain`, `filterfalse`, `takewhile`, ...) already works
on them directly - no bespoke re-implementation needed for those.

Deliberately deferred at that time: collection-level operations that fold a
*collection* of `Option`/`Result` values into one `Option`/`Result`, with
short-circuiting on the first failure - `sequence` and `traverse` in the
Haskell/Rust sense. This spec covers that gap, plus two things identified
during design: a non-short-circuiting `partition` (collect every success
*and* every failure), and `values` (a named wrapper around the
`itertools.chain.from_iterable` "flatten to just the present/Ok values"
trick).

## Scope

**In scope:**
- `sequence_option`/`sequence_result` - fold `Iterable[Option[T]]` /
  `Iterable[Result[T, E]]` into one `Option[list[T]]` / `Result[list[T], E]`,
  short-circuiting on the first `Nothing`/`Err`.
- `traverse_option`/`traverse_result` - map a function returning
  `Option`/`Result` over an iterable, then sequence, short-circuiting so the
  function is never called on items after the first failure.
- `partition_option`/`partition_result` - split a collection into successes
  and failures without short-circuiting (collects everything).
- `sequence`/`traverse`/`partition` - `@overload`-typed polymorphic wrappers
  over the six functions above, for callers who don't want to pick the
  `_option`/`_result` suffix by hand.
- `values` - a named wrapper for the free `itertools.chain.from_iterable`
  interop trick.
- `Option.sequence`/`Option.traverse` and `Result.sequence`/`Result.traverse`
  classmethod factories delegating to the free functions above, mirroring
  the existing `Option.from_nullable`/`Result.of` classmethod-factory
  pattern.

**Out of scope:**
- Re-implementing plain `itertools` functions (`chain`, `filterfalse`,
  `takewhile`, `dropwhile`, `islice`, ...) against `Option`/`Result` - these
  already work for free via the existing `__iter__`, and duplicating them
  would just be worse, `Option`/`Result`-only copies of things Python
  already provides.
- Classmethod factories for `partition`/`values` - these don't return an
  `Option`/`Result` to construct, so there's no natural classmethod shape
  for them (unlike `sequence`/`traverse`, which do produce an
  `Option`/`Result`).
- Async iteration support.

## Module

New file `logerr/itertools.py`, core (no extra dependencies beyond stdlib
`itertools`/`typing`), following the same pattern as `logerr/functools.py`:
plain module-level functions, not exported from top-level
`logerr/__init__.py` - callers write
`from logerr.itertools import sequence, traverse, partition, values`.

`import itertools` inside `logerr/itertools.py` resolves to the stdlib
module (Python 3's absolute-import default), not a self-import - this is
the same safe pattern as any package submodule sharing a name with a
stdlib module.

## The Six Concrete Functions

```python
def sequence_option[T](items: Iterable[Option[T]]) -> Option[list[T]]: ...
def sequence_result[T, E](items: Iterable[Result[T, E]]) -> Result[list[T], E]: ...
def traverse_option[T, U](items: Iterable[T], func: Callable[[T], Option[U]]) -> Option[list[U]]: ...
def traverse_result[T, U, E](items: Iterable[T], func: Callable[[T], Result[U, E]]) -> Result[list[U], E]: ...
def partition_option[T](items: Iterable[Option[T]]) -> tuple[list[T], int]: ...
def partition_result[T, E](items: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]: ...
```

**Semantics:**

- `sequence_option`/`sequence_result`: iterate `items`; on the first
  `Nothing`/`Err`, stop and return it (`Nothing.empty()` for the Option
  side, matching the `and_option`/`flatten_option` precedent of not
  propagating the original reason; `Err(e, _skip_logging=True)` for the
  Result side, matching `zip_result`/`flatten_result`/`and_result`'s
  existing re-wrap-without-double-logging pattern). Otherwise collect every
  value into a `list` and return `Some(values)`/`Ok(values)`.
  `sequence_option([])` is `Some([])`; `sequence_result([])` is `Ok([])` -
  well-defined because the caller already committed to Option-vs-Result by
  choosing the function name.
- `traverse_option`/`traverse_result`: implemented as
  `sequence_option(func(item) for item in items)` (and the `_result`
  equivalent) - a generator expression, so `sequence_option`'s early
  `return` on the first failure means `func` is never called on items
  after that point. No duplicated collect logic between `traverse_*` and
  `sequence_*`.
- `partition_option`/`partition_result`: always iterate every item (no
  short-circuit - the point is to collect all failures, not stop at the
  first). `partition_option` returns `(values, nothing_count)` where
  `nothing_count` is a plain `int` (Nothing carries no real payload beyond
  an optional reason string, so counting rather than collecting reasons
  avoids inventing meaning for absent reasons). `partition_result` returns
  `(oks, errs)` where `errs` is the actual list of error values.
- If `func` (in `traverse_*`) raises an exception, it propagates uncaught -
  consistent with `map`/`then`/`filter`'s existing no-catch semantics
  established for `logerr.option`/`logerr.result`. These functions don't
  introduce a new exception-handling policy.

## The Three Polymorphic Wrappers

```python
@overload
def sequence(items: Iterable[Option[T]]) -> Option[list[T]]: ...
@overload
def sequence(items: Iterable[Result[T, E]]) -> Result[list[T], E]: ...
def sequence(items): ...  # runtime implementation, see below

# same @overload shape for traverse(items, func) and partition(items)
```

Runtime behavior (shared shape across all three):

1. Peek at the first element (`next(iter(items))` for `sequence`; for
   `traverse`, call `func` on the first item and inspect *that* result,
   since the input items aren't Option/Result themselves; for `partition`,
   materialize to a `list` first since it needs full traversal anyway).
2. If the peeked value is empty (`StopIteration` / empty list): raise
   `ValueError` with a message pointing at the concrete
   `sequence_option([])`/`sequence_result([])` (etc.) as the unambiguous
   alternative.
3. Otherwise `isinstance(first, (Some, Nothing))` routes to the `_option`
   function, `isinstance(first, (Ok, Err))` routes to the `_result`
   function, feeding the already-peeked first value back in via
   `itertools.chain([first], rest)` so nothing is consumed twice (and for
   `traverse`, `func` is never called twice on the first item).
4. Anything else: raise `TypeError` naming the actual type seen.

## `values`

```python
@overload
def values[T](items: Iterable[Option[T]]) -> Iterator[T]: ...
@overload
def values[T](items: Iterable[Result[T, Any]]) -> Iterator[T]: ...
def values(items):
    """Yield the present/Ok values from a collection of Options/Results, dropping the rest."""
    return itertools.chain.from_iterable(items)
```

No Option-vs-Result *runtime* dispatch is needed here - the single
implementation body is identical either way (`chain.from_iterable` just
iterates whatever it's given) - but `@overload` still gives precise typing
for both call shapes without unifying `E` and `T` into one signature-level
union. `values([Some(1), Nothing.empty(), Some(3)])` yields
`1, 3`; `values([Ok(1), Err("boom"), Ok(3)])` yields `1, 3`. Lazy, and
distinct in purpose from `partition_*` (which is eager and also keeps
failure information; `values` only wants the successes and doesn't care
how many/which items failed).

## Classmethod Factories on `Option`/`Result`

Defined once on the abstract `Option`/`Result` base classes (same placement
as the existing `from_nullable`/`from_predicate`/`of` classmethods - not
duplicated across `Some`/`Nothing`/`Ok`/`Err`, since a classmethod factory
doesn't need `self`):

```python
# logerr/option.py, on the Option class
@classmethod
def sequence[T](cls, items: Iterable[Option[T]]) -> Option[list[T]]:
    from .itertools import sequence_option
    return sequence_option(items)

@classmethod
def traverse[T, U](cls, items: Iterable[T], func: Callable[[T], Option[U]]) -> Option[list[U]]:
    from .itertools import traverse_option
    return traverse_option(items, func)
```

```python
# logerr/result.py, on the Result class
@classmethod
def sequence[T, E](cls, items: Iterable[Result[T, E]]) -> Result[list[T], E]:
    from .itertools import sequence_result
    return sequence_result(items)

@classmethod
def traverse[T, U, E](cls, items: Iterable[T], func: Callable[[T], Result[U, E]]) -> Result[list[U], E]:
    from .itertools import traverse_result
    return traverse_result(items, func)
```

Deferred (inline) imports match the existing pattern used for
`zip`/`flatten`/`and_`/`or_` methods importing from `.functools` - avoids a
circular import, since `logerr/itertools.py` imports `Option`/`Result` at
module level.

`partition`/`values` get no classmethod - they don't return an
`Option`/`Result`, so there's nothing to construct via a factory.

## Testing

`tests/unit/test_itertools.py`, TDD, mirroring `test_functools.py`'s class
structure: one test class per function (`TestSequenceOption`,
`TestSequenceResult`, `TestTraverseOption`, `TestTraverseResult`,
`TestPartitionOption`, `TestPartitionResult`, `TestSequencePolymorphic`,
`TestTraversePolymorphic`, `TestPartitionPolymorphic`, `TestValues`), plus
short-circuit tests proving `traverse_*` doesn't call `func` past the first
failure (e.g. a counting wrapper function asserting call count), and
`ValueError`/`TypeError` tests for the polymorphic wrappers' edge cases.
Classmethod factory tests added to `TestOptionCombinatorMethods`-style
classes in `test_option.py`/`test_result.py`.

## Docs

- `logerr/itertools.pyi` type stub.
- `docs/api/itertools.md` mkdocstrings page + `mkdocs.yml` nav entry.
- New "Collecting Options/Results" subsection in
  `docs/guide/option-types.md`/`docs/guide/result-types.md`, including a
  documentation-only note about the free `itertools.chain.from_iterable`/
  `values()` interop (no new code involved in that part - just showing it
  works).
- `CHANGELOG.md` entry under `### Added`.
- `CLAUDE.md` gets a `logerr.itertools` section alongside the existing
  "Combinator Methods on Option/Result" one.
