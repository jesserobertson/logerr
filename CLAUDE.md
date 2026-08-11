# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**logerr** is a Python library that provides Rust-like Option and Result types with automatic logging integration. It builds upon the elegant API design from [MaT1g3R/option](https://github.com/MaT1g3R/option), extending it with enhanced logging capabilities through loguru and configuration management via confection.

Key features:
- Rust-like Option<T> and Result<T, E> types with full type safety
- Automatic logging of Result/Err cases to loguru  
- Configuration management through confection
- Comprehensive testing with pytest and hypothesis
- Full mypy type checking support

## Development Commands

### Environment Management
- `pixi info` - Show project and environment information
- `pixi install` - Install dependencies
- `pixi shell` - Activate the pixi environment
- `pixi shell -e dev` - Activate environment with dev dependencies (`pixi shell` only accepts `-e`/`--environment`, not `--feature`)
- `pixi shell -e docs` - Activate environment with documentation dependencies
- `pixi shell -e retry` - Activate environment with retry recipes (tenacity)
- `pixi shell -e tables` - Activate environment with dataframe/table recipes (pandas, pymongo)

### Testing and Quality

`test` and `quality` are Typer apps (`scripts/test.py`, `scripts/quality.py`) and require a subcommand — running `pixi run -e dev test` bare errors with "Missing command"; `pixi run -e dev quality` bare defaults to `quality check`.

- `pixi run -e dev test fast` - Run fast tests only (excludes slow tests)
- `pixi run -e dev test unit` / `test integration` - Run a specific test tier
- `pixi run -e dev test all` - Run all tests including doctests from documentation and README
- `pixi run -e dev pytest <args>` - Run pytest directly with custom arguments and flags
- `pixi run -e dev quality typecheck` - Run type checking with mypy
- `pixi run -e dev quality` - Run all quality checks (mypy typecheck + ruff lint + format check)
- `pixi run -e dev check-all` - Run all checks (test all + quality) - **REQUIRED BEFORE COMMITS**

#### Available Test Markers:
- `unit` - Unit tests for core functionality
- `integration` - Integration tests
- `recipes` - Tests for recipes module functionality
- `dataframes` - Tests for dataframes functionality (requires pandas/polars)
- `mongo` - Tests requiring MongoDB connection
- `slow` - Slow-running tests (excluded from default test run)
- `network` - Tests requiring network access
- `property` - Property-based tests using hypothesis

#### Example Test Commands:
```bash
# Run only unit tests
pixi run -e dev pytest tests/ -m unit --cov=logerr

# Run integration and recipes tests
pixi run -e dev pytest tests/ -m "integration or recipes" --cov=logerr

# Run all except slow tests (same as default test command)
pixi run -e dev pytest tests/ --doctest-modules logerr -m "not slow" --cov=logerr

# Run everything including slow tests
pixi run -e dev pytest tests/ --doctest-modules logerr --cov=logerr

# Run specific test file
pixi run -e dev pytest tests/unit/test_option.py -v

# Run with specific coverage report
pixi run -e dev pytest tests/ --cov=logerr --cov-report=html -m unit
```

### Documentation

`scripts/docs.py` needs both `typer` (a `dev`-feature dependency) and
`mkdocs` (a `docs`-feature dependency), so it only works under the
`default` environment (which combines both) - `-e docs` alone is missing
`typer` and will fail with `ModuleNotFoundError`.

- `pixi run docs build` - Build documentation (uses the default environment; no `-e` flag)
- `pixi run docs serve` - Serve documentation locally

### Package Management
- Add dependencies: `pixi add <package-name>`
- Add development dependencies: `pixi add --feature dev <package-name>`
- Add documentation dependencies: `pixi add --feature docs <package-name>`
- Add retry dependencies: `pixi add --feature retry <package-name>`
- Add tables dependencies: `pixi add --feature tables <package-name>`
- Remove dependencies: `pixi remove <package-name>`

## Project Structure

```
logerr/
├── logerr/                    # Main library package
│   ├── __init__.py            # Main exports (Option, Some, Nothing, Result, Ok, Err)
│   ├── option.py               # Option<T>, Some<T>, Nothing implementation
│   ├── result.py               # Result<T, E>, Ok<T>, Err<E> implementation
│   ├── config.py               # Core configuration (basic enabled/level)
│   ├── utilities.py            # All utility functions (execute, nullable, log, validate, resolve, chain, attribute, error, pipe, try_chain)
│   └── recipes/                # Optional extended functionality (heavy deps only)
│       ├── __init__.py
│       ├── config.py            # Advanced per-library/confection config
│       ├── retry.py             # Retry decorators/utilities (feature: retry, needs tenacity)
│       └── dataframes/          # DataFrame/Mongo conversion (feature: tables, needs pandas/pymongo)
│           ├── __init__.py
│           ├── conversion.py
│           ├── mongo.py
│           ├── quality.py
│           └── types.py
├── scripts/                    # Typer-based task scripts invoked by pixi tasks
│   ├── test.py                  # test task (unit/integration/all/fast/clean)
│   ├── quality.py                # quality task (lint/format/typecheck/check/fix)
│   ├── dev.py
│   ├── build.py
│   └── docs.py
├── docs/                       # Documentation
│   ├── api/                     # API reference documentation
│   │   ├── config.md
│   │   ├── option.md
│   │   └── result.md
│   ├── guide/                    # User guides
│   │   ├── getting-started.md
│   │   ├── result-types.md
│   │   ├── option-types.md
│   │   ├── configuration.md
│   │   └── examples.md
│   └── index.md                 # Documentation homepage
├── tests/                       # Test package
│   ├── conftest.py
│   ├── unit/                     # Core Option/Result/utils tests + hypothesis property tests
│   ├── integration/               # Cross-type integration tests
│   └── recipes/                   # Tests for recipes/ (retry, config, utilities, dataframes/)
├── mkdocs.yml                    # Documentation configuration
├── pixi.toml                     # Project configuration and dependencies
├── pyproject.toml                # PyPI packaging configuration
├── README.md                     # Project README
└── CLAUDE.md                     # This file
```

## Dependencies

### Runtime Dependencies
- **loguru**: Automatic logging of Result/Err cases
- **confection**: Configuration management

### Optional Dependencies (feature: retry)
- **tenacity**: Retry decorators and utilities for resilient operations

### Optional Dependencies (feature: tables)
- **pandas**: DataFrame conversion for recipes.dataframes
- **pymongo**: MongoDB access for recipes.dataframes

### Development Dependencies (feature: dev)
- **pytest**: Test framework
- **hypothesis**: Property-based testing
- **mypy**: Static type checking
- **ruff**: Linting and code formatting
- **pytest-cov**: Test coverage reporting
- **pre-commit**: Git hooks for code quality

### Documentation Dependencies (feature: docs)
- **mkdocs**: Documentation site generator
- **mkdocs-material**: Material theme for mkdocs
- **mkdocstrings**: API documentation from docstrings
- **mkdocstrings-python**: Python handler for mkdocstrings

## Architecture Notes

The library aims to replicate Rust's Option and Result types with Python's type system:
- Full generic type support with TypeVar constraints
- Pattern matching through method chaining and `match()` methods
- Automatic logging integration for error cases
- Configuration-driven behavior through confection
- Comparison operators (`<`, `<=`, `>`, `>=`) implemented directly on Some/Nothing/Ok/Err via `match`-based type narrowing
- Comprehensive factory functions for creating Options and Results

### Functional Programming Style

**Preferred**: Use functional API patterns with pipeline-style chaining:

```python
# Good: Functional pipeline with inline lambdas for simple operations
def load_config(path: str) -> Result[Config, Exception]:
    return (
        Result.from_predicate(
            path,
            lambda p: Path(p).exists(),
            FileNotFoundError(f"Config not found: {path}")
        )
        .then(lambda p: Result.of(lambda: Config().from_disk(p)))
        .map(lambda config: config.get("app_section", {}))
    )

# Good: Use Option for nullable values
def get_setting(key: str) -> Option[str]:
    return Option.from_nullable(config.get(key))

# Good: Chain operations instead of nested conditionals  
result = (
    get_user_input()
    .filter(lambda x: len(x) > 0)
    .map(str.upper)
    .unwrap_or("DEFAULT")
)
```

**Avoid**: Imperative try/catch patterns when functional alternatives exist:

```python
# Less preferred: Manual exception handling
def load_config(path: str) -> Result[Config, Exception]:
    try:
        if not Path(path).exists():
            return Err.from_exception(FileNotFoundError("Config not found"))
        config = Config().from_disk(path)
        return Ok(config)
    except Exception as e:
        return Err.from_exception(e)
```

**Guidelines**:
- Use inline lambdas for simple operations (1-2 lines)
- Extract complex logic into separate functions when lambdas become unreadable
- Prefer `Result.of`, `Result.from_predicate`, `Option.from_nullable` over manual construction
- Use method chaining (.then, .map, .filter) for sequential operations
- Avoid deep nesting - flatten with functional composition
- **Use utility functions from `logerr.utilities` for common patterns**

## Common Functional Patterns & Utilities

`logerr.utilities` provides all of logerr's functional utility functions - `execute`, `nullable`, `log`, `validate`, `resolve`, `chain`, `attribute`, `error`, `pipe`, `try_chain`. None of them depend on tenacity/pandas/pymongo, so they all live in core rather than being split across `recipes` - there's nothing "advanced" about them dependency-wise.

### **Safe Execution Pattern**
Use `execute()` instead of manual try/catch blocks:

```python
# Good: Using utility function
from logerr.utilities import execute

result = execute(lambda: risky_operation())
option_result = execute(lambda: maybe_none(), return_type="option")

# Less preferred: Manual try/catch
try:
    value = risky_operation()
    return Ok(value)
except Exception as e:
    return Err.from_exception(e)
```

### **Nullable Value Handling**
Use `nullable()` for consistent None handling:

```python
# Good: Standardized nullable handling
from logerr.utilities import nullable

def get_config_value(key: str) -> Option[str]:
    raw_value = config.get(key)
    return nullable(raw_value, log_absence=True)

# For Result types with custom errors:
def validate_required_field(value: str | None) -> Result[str, ValueError]:
    return nullable(
        value,
        return_type="result", 
        error_factory=lambda: ValueError(f"Required field missing")
    )
```

### **Validation with Predicates**
Use `validate()` for consistent validation logic:

```python
# Good: Reusable validation pattern
from logerr.utilities import validate, error

def validate_log_level(level: str) -> Result[str, ValueError]:
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    return validate(
        level,
        lambda x: x in valid_levels,
        error_factory=error(level, "log level", valid_levels)
    )
```

### **Safe Attribute Access**
Use `attribute()` for exception-safe attribute access:

```python
# Good: Safe attribute access
from logerr.utilities import attribute

func_name = attribute(func, "__name__", "callable")
logger.debug(f"Executing {func_name}")

# Less preferred: Manual hasattr checking
func_name = func.__name__ if hasattr(func, "__name__") else "callable"
```

### **Context-Aware Logging**
Use `log()` for consistent logging with caller information:

```python
# Good: Centralized context logging
from logerr.utilities import log

def handle_error(error: Exception) -> None:
    log(
        f"Operation failed: {error}",
        log_level="ERROR",
        extra_context={"error_type": type(error).__name__}
    )
```

### **Parameter Resolution**
Use `resolve()` for consistent parameter handling:

```python
# Good: Functional parameter resolution
from logerr.utilities import resolve

def retry_operation(max_attempts: int | None = None) -> None:
    actual_attempts = resolve(
        max_attempts, 
        default=3,
        validator=lambda x: x > 0
    )
```

### **Available Utility Functions**

**`logerr.utilities`** (all core, no extra dependencies):

| Function | Purpose | Common Use Cases |
|----------|---------|------------------|
| `execute()` | Execute callables with automatic Result/Option wrapping | Factory functions, risky operations |
| `nullable()` | Convert None values to appropriate types | Configuration loading, optional parameters |
| `log()` | Context-aware logging with caller information | Error logging, debugging |
| `validate()` | Predicate-based validation with consistent error handling | Input validation, constraint checking |
| `resolve()` | Parameter resolution with validation | Function parameters, configuration merging |
| `chain()` | Exception-safe method chaining | Recovering the old catch-and-convert behavior for map/then/filter |
| `attribute()` | Safe attribute access | Getting function names, object properties |
| `error()` | Standardized validation error messages | Consistent error formatting |
| `pipe()` | Pipeline-style composition of functions | Multi-step transforms without nesting |
| `try_chain()` | Try callables in order, return first success | Fallback strategies |
| `wrap_result()` | Decorate a function so exceptions -> Err, returned Result passes through, plain value -> Ok | Mixing ordinary code (context managers, multiple statements) with Result-returning calls without manual try/except |
| `wrap_option()` | Decorate a function so exceptions -> Nothing, returned Option passes through, plain value -> Some/None -> Nothing | Same as wrap_result(), for Option-returning functions |

`wrap_result()`/`wrap_option()` solve a different problem than `execute()`:
`execute()` wraps a single callable's *return value*; `wrap_result()`/
`wrap_option()` decorate a whole function so its *body* can mix ordinary
imperative code (context managers, multiple statements) with
Result/Option-returning calls, with no manual `try/except` and no
`unwrap_err()`-then-rewrap when a call already returns a `Result`/`Option`:

```python
@wrap_result
def pull_all(settings, feature_refs) -> Result[list[Feature], Exception]:
    with httpx.Client() as http_client:
        return traverse_result(
            feature_refs,
            lambda ref: pull_feature(http_client, ref, settings.data_dir / "features"),
        )
```

### **Combinator Methods on Option/Result**

`Some`/`Nothing`/`Ok`/`Err` also have `zip()`, `flatten()`, `and_()`, `or_()` methods (plus `ok()`/`err()` on `Result`), implemented as thin delegates to free functions in `logerr.functools` (`zip_option`, `zip_result`, `flatten_option`, `flatten_result`, `and_option`, `and_result`, `or_option`, `or_result`, `ok`, `err`). None of these invoke a callable, so - unlike `map`/`then`/`filter`/`or_else` - there's no exception-propagation question: a `Nothing`/`Err` input just propagates as-is.

`Option`/`Result` are also iterable now (`__iter__` yields the value 0 or 1 times - `Nothing`/`Err` yield nothing, `Some`/`Ok` yield their value once), matching Rust's own `Option::iter()`/`Result::iter()`. This means Python's own `zip()` and the standard `itertools` toolkit already work correctly on `Option`/`Result` values directly - there's deliberately no bespoke `logerr` `zip()` wrapper that could behave differently from the real one depending on what you pass it.

### **Collection Operations: `logerr.itertools`**

`logerr.itertools` adds what plain `itertools` has no equivalent for -
folding a *collection* of `Option`/`Result` values into one, with
short-circuit-on-first-failure semantics: `sequence_option`/
`sequence_result`, `traverse_option`/`traverse_result` (map then sequence,
short-circuiting), `partition_option`/`partition_result` (collect
successes *and* failures, no short-circuit), and `fold_option`/
`fold_result` (thread an accumulator through a sequence of items via an
Option/Result-returning step function, short-circuiting on the first
failure - mirrors Rust's `Iterator::try_fold`; unlike `sequence`/
`traverse`, each step's output feeds the next step's input, so it's
explicitly sequential rather than order-independent). `sequence`/
`traverse`/`partition`/`fold` also exist as `@overload`-typed polymorphic
wrappers dispatching on runtime type (raising `ValueError` on empty input,
since there's no element to dispatch on - use the `_option`/`_result`
function directly in that case). `values()` names the existing free
`itertools.chain.from_iterable` interop trick (flatten to just the
present/Ok values). `Option.sequence`/`Option.traverse`/`Option.fold` and
`Result.sequence`/`Result.traverse`/`Result.fold` classmethod factories
delegate to the free functions, mirroring the existing
`Option.from_nullable`/`Result.of` classmethod-factory pattern.

## API Structure

The library provides a clean, namespaced API:

### Direct Type Imports
```python
from logerr import Ok, Err, Some, Nothing, Result, Option
```

### Configuration Functions
```python
# Core (basic enabled/level toggle)
from logerr import configure, get_config, reset_config

# Advanced (per-library config, confection files) — not exported at top level
from logerr.recipes.config import configure_advanced, configure_from_confection
```

### Factory Functions (Class Methods)
```python
from logerr import Result, Option

# Result factories
result = Result.of(lambda: some_function())
result = Result.from_optional(maybe_value, "was None")

# Option factories  
option = Option.from_nullable(dict.get("key"))
option = Option.of(lambda: expensive_computation())
option = Option.from_predicate(value, lambda x: x > 0)
```

### Configuration Examples
```python
# Core configuration — flat kwargs only, no dict/libraries support
logerr.configure(enabled=True, level="WARNING")

# Get current configuration
config = logerr.get_config()

# Reset to defaults
logerr.reset_config()
```

Per-library config and confection-file loading are advanced features in `logerr.recipes.config`, not the core API:

```python
from logerr.recipes.config import configure_advanced, configure_from_confection

# Per-library configuration (dict-based)
configure_advanced({"level": "WARNING", "libraries": {"mylib": {"level": "DEBUG"}}})

# From a confection config file (expects a top-level "logerr" section)
configure_from_confection("config.cfg")
```


## Code Quality Requirements

**CRITICAL**: Always run code quality checks before committing any changes:

1. **Run all checks**: `pixi run -e dev check-all`
   - This runs: tests, type checking (mypy), and code quality (ruff)
   - This mirrors the exact checks run in GitHub CI
   - **ALL CHECKS MUST PASS** before committing

2. **Pre-commit hooks installed**: The repository uses pre-commit hooks that automatically run:
   - Ruff linting and format checking
   - MyPy type checking  
   - All quality checks (check-all command)
   - Tests are available as manual pre-commit hook

3. **Individual quality commands**:
   - `pixi run -e dev test fast` - Run test suite (fast tests only)
   - `pixi run -e dev quality typecheck` - Run mypy type checking
   - `pixi run -e dev quality` - Run mypy typecheck + ruff lint + format checks

## Configuration

- **Platform**: macOS ARM64 (osx-arm64)
- **Package channels**: conda-forge
- **Environment**: Uses pixi for dependency management and virtual environments