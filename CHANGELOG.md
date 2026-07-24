# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project is pre-1.0; breaking changes may land in minor versions until
a 1.0 stability commitment is made.

## [Unreleased]

### Breaking Changes

- `pipe()` now returns `Result[Any, Exception]` instead of the raw final
  value, short-circuiting on the first step that raises (previously it had
  no error handling at all, unlike every other function in
  `logerr.utilities`). Callers need `.unwrap()` (or `.map()`/`.unwrap_or()`)
  to get the value out.
- `logerr.recipes.utilities` removed entirely. Its 7 functions (`validate`,
  `resolve`, `chain`, `attribute`, `error`, `pipe`, `try_chain`) had no
  dependency on tenacity/pandas/pymongo - the `recipes` split served no
  dependency-isolation purpose for them, so they moved into core
  `logerr.utilities` alongside `execute`/`nullable`/`log`. Update
  `from logerr.recipes.utilities import ...` to `from logerr.utilities import ...`.

- `Some.map`/`.then`/`.filter`, `Nothing.or_else`/`.ok_or_else`, `Ok.map`/`.then`,
  and `Err.map_err`/`.or_else` no longer catch exceptions raised by the
  function passed to them. Previously, any exception (including bugs like a
  typo causing `AttributeError`) was silently converted into a `Nothing`/`Err`,
  which could mask real programming errors as ordinary domain failures. These
  methods now match Rust's `Option`/`Result` semantics: exceptions propagate to
  the caller. Exception-to-`Option`/`Result` conversion is still available at
  explicit entry points: `Option.of`/`from_predicate`, `Result.of`/`from_predicate`,
  and `logerr.utilities.execute`.
- `logerr.utils` renamed to `logerr.utilities` (matches `logerr.recipes.utilities`
  naming). Update `from logerr.utils import ...` to `from logerr.utilities import ...`.
- `logerr[recipes]` split into `logerr[retry]` (tenacity) and `logerr[tables]`
  (pandas, pymongo) so consumers who only want retry decorators aren't forced
  to pull in pandas/pymongo.
- `Result.retry` (a method injected onto the core `Result` class by importing
  `logerr.recipes.retry`) has been removed. Use the standalone
  `logerr.recipes.retry.retry_if_err()` function instead.
- `execute()`'s `on_exception` keyword argument renamed to `return_type`, matching
  `nullable()`/`validate()`'s naming for the same concept.

### Added

- `Option.ok_or(err)` and `Option.ok_or_else(err_fn)` - convert an `Option` into
  a `Result`, matching Rust's `Option::ok_or`/`ok_or_else`. Previously missing
  entirely.
- `Result.unwrap_err()` is now declared on the abstract `Result` base class
  (previously only concretely implemented on `Ok`/`Err`), so code that holds a
  value typed as the general `Result[T, E]` can call `.unwrap_err()` without a
  type error. This was a real, previously mypy-cache-masked gap: `logerr/recipes/retry.py`
  and `logerr/recipes/dataframes/mongo.py` both called `.unwrap_err()` on
  generically-typed `Result` values, which mypy failed to flag only because of
  a stale `.mypy_cache`; a clean run reproduced the errors.
- `execute()`/`nullable()` now have `@overload` signatures keyed on the
  `return_type` literal, so callers get a precise `Option[T]` or `Result[T, E]`
  instead of `Any`.
- `CHANGELOG.md` (this file).

### Fixed

- `execute()` discarded falsy `default_error` values (`0`, `""`, `False`) via
  a truthy `or` check, silently using the caught exception instead.
- `Nothing.unwrap()` always raised a generic `ValueError`, unlike
  `Err.unwrap()` which re-raises the original exception when available.
  `Nothing` now preserves the original exception (via `from_exception()`) so
  `unwrap()` behaves consistently between the two types.
- `logerr.recipes.retry`'s tests were mistagged `integration`, which silently
  skipped all 31 of them in every documented workflow (no task passes
  `--run-integration`).
- Three hypothesis property-test files under `tests/unit/` weren't matching
  pytest's `test_*.py` collection pattern and never actually ran; renamed to
  `test_hypothesis_*.py`.
- `scripts/quality.py`'s `check()` command caught `typer.Exit` to detect
  failures, but the underlying `run_command()` never raised it - so
  mypy/ruff/format failures were silently reported as "Pass" and `check-all`
  always exited 0 regardless of real errors.
- `pixi.toml`'s deprecated `[project]` table renamed to `[workspace]`.
- `dev` pixi environment now includes the `retry`/`tables` feature
  dependencies, so recipes tests actually run instead of failing to import
  pandas/pymongo/tenacity.
- `docs/guide/configuration.md` and README's Advanced Configuration section
  described a `logerr.configure()` API that doesn't exist (a dict-based call
  with a `libraries` key, and a top-level `configure_from_confection` that
  isn't exported). Rewritten to match the real API:
  `logerr.configure(enabled=, level=)` for basic use,
  `logerr.recipes.config.configure_advanced()`/`configure_from_confection()`
  for per-library/file-based config.
- `docs/guide/getting-started.md` had a missing code-fence opening around a
  "Chain operations" example, which caused the following two section headings
  to be swallowed into a garbled code block when rendered.
- `nullable(value, return_type="result", log_absence=False)` still logged via
  `Err.from_value()` regardless of `log_absence` - only the `Option` branch
  honored the flag. Both branches now respect it.
- `logerr/recipes/retry.py` reached into `Result`'s private `_error` attribute
  via `getattr`/`hasattr` instead of the public `unwrap_err()`; refactored to
  use the public API (also removes several now-unreachable defensive branches).
- Docs/docstrings in `logerr/recipes/dataframes/__init__.py`, `mongo.py`, and
  README referenced a nonexistent `Result.unwrap_or_default()`; fixed to use
  the real `unwrap_or(default)`.
- Removed `logerr/protocols.py`/`protocols.pyi` (dead code - comparison protocol
  definitions never imported anywhere; comparisons are implemented directly on
  `Some`/`Nothing`/`Ok`/`Err` via `match`-based type narrowing).
- CLAUDE.md's "Functional Programming Style" section taught `Result.from_callable()`
  and `.and_then()` as the preferred API - neither exists anywhere in the
  codebase. The real methods are `Result.of()`/`Option.of()` and `.then()`,
  which `docs/guide/getting-started.md` already used correctly. All CLAUDE.md
  examples now use the real method names.

### Added (CI/tooling)

- `scripts/check_version_sync.py` + `pixi run -e dev check-version-sync`:
  fails if the version string in pixi.toml, pyproject.toml, and
  logerr/__init__.py ever diverge. Wired into `check-all` (so it also runs
  in the pre-commit hook) and as a dedicated CI step.

- `mypy` config replaced with `strict = true` - the codebase was already
  clean under full strict mode (confirmed by running it directly before
  adopting), so there was no reason to hand-pick a subset of flags.
- `ruff` select list gained `SIM` (flake8-simplify), `RUF` (ruff-specific),
  `N` (pep8-naming), and `PTH` (flake8-use-pathlib). Deliberately left out
  `PIE`/`RET`/`PT`/`ARG` - each surfaced 30-190+ findings, mostly stylistic
  churn (unused mock-callback args, `else` after `return`) rather than real
  issues, too invasive for this pass. Fixed the 25 findings the adopted
  categories surfaced, including 6 stale `# type: ignore[no-any-return]`
  comments in mongo.py that `warn_unused_ignores` caught - dead weight left
  over from before `execute()` got precise overloads.

### Changed (CI/tooling)

- `.pre-commit-config.yaml`: removed the separate always-run `ruff-check`/
  `ruff-format`/`mypy` hooks - `check-all` (also always-run) already covers
  all three, so they were silently running twice on every commit.

### Test Coverage

- `logerr/recipes/dataframes/{conversion,mongo,quality}.py`: 10-37% -> 100%
  (previously had no dedicated test files at all).
- `logerr/recipes/retry.py`: ~15-39% -> 96%.
- Overall project coverage: 65% -> 97%.
