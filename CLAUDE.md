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
- `pixi shell --feature dev` - Activate environment with dev dependencies
- `pixi shell --feature docs` - Activate environment with documentation dependencies
- `pixi shell --feature recipes` - Activate environment with recipes module (retry patterns)

### Testing and Quality
- `pixi run -e dev test` - Run test suite (fast tests only, excludes slow tests)
- `pixi run -e dev test-all` - Run all tests including doctests from documentation and README
- `pixi run -e dev pytest <args>` - Run pytest with custom arguments and flags
- `pixi run -e dev typecheck` - Run type checking with mypy
- `pixi run -e dev quality` - Run code quality checks (ruff lint + format check)
- `pixi run -e dev check-all` - Run all checks (test, typecheck, quality) - **REQUIRED BEFORE COMMITS**

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
pixi run -e dev pytest tests/test_option.py -v

# Run with specific coverage report
pixi run -e dev pytest tests/ --cov=logerr --cov-report=html -m unit
```

### Documentation
- `pixi run -e docs docs-serve` - Serve documentation locally
- `pixi run -e docs docs-build` - Build documentation

### Package Management
- Add dependencies: `pixi add <package-name>`
- Add development dependencies: `pixi add --feature dev <package-name>`
- Add documentation dependencies: `pixi add --feature docs <package-name>`
- Add recipes dependencies: `pixi add --feature recipes <package-name>`
- Remove dependencies: `pixi remove <package-name>`

## Project Structure

```
logerr/
├── logerr/           # Main library package
│   ├── __init__.py   # Main exports (Option, Some, Nothing, Result, Ok, Err)
│   ├── option.py     # Option<T>, Some<T>, Nothing implementation
│   ├── result.py     # Result<T, E>, Ok<T>, Err<E> implementation
│   ├── config.py     # Configuration management via confection
│   ├── utils.py      # Reusable utility functions for functional patterns
│   ├── protocols.py  # Type protocols for comparison support
│   └── recipes/      # Optional extended functionality
│       ├── __init__.py
│       └── retry.py  # Retry decorators and utilities with tenacity integration
├── docs/             # Documentation
│   ├── api/          # API reference documentation  
│   │   ├── config.md
│   │   ├── option.md
│   │   └── result.md
│   ├── guide/        # User guides
│   │   ├── getting-started.md
│   │   ├── result-types.md
│   │   ├── option-types.md
│   │   ├── configuration.md
│   │   └── examples.md
│   └── index.md      # Documentation homepage
├── tests/            # Test package
│   ├── test_api.py
│   ├── test_comparisons.py
│   ├── test_enhanced_predicates.py
│   ├── test_option.py
│   ├── test_result.py
│   ├── test_retry.py
│   └── test_utils.py
├── mkdocs.yml        # Documentation configuration
├── pixi.toml         # Project configuration and dependencies
├── README.md         # Project README
└── CLAUDE.md         # This file
```

## Dependencies

### Runtime Dependencies
- **loguru**: Automatic logging of Result/Err cases
- **confection**: Configuration management

### Optional Dependencies (feature: recipes)  
- **tenacity**: Retry decorators and utilities for resilient operations

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
- Comparison support via type protocols
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
        .and_then(lambda p: Result.from_callable(lambda: Config().from_disk(p)))
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
- Prefer `Result.from_callable`, `Result.from_predicate`, `Option.from_nullable` over manual construction
- Use method chaining (.and_then, .map, .filter) for sequential operations
- Avoid deep nesting - flatten with functional composition
- **Use utility functions from `logerr.utils` for common patterns**

## Common Functional Patterns & Utilities

The `logerr.utils` module provides reusable utility functions for common functional patterns. These eliminate code duplication and provide consistent APIs across the library.

### **Safe Execution Pattern**
Use `execute()` instead of manual try/catch blocks:

```python
# Good: Using utility function
from logerr.utils import execute

result = execute(lambda: risky_operation())
option_result = execute(lambda: maybe_none(), on_exception="option")

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
from logerr.utils import nullable

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
from logerr.utils import validate, error

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
from logerr.utils import attribute

func_name = attribute(func, "__name__", "callable")
logger.debug(f"Executing {func_name}")

# Less preferred: Manual hasattr checking
func_name = func.__name__ if hasattr(func, "__name__") else "callable"
```

### **Context-Aware Logging**
Use `log()` for consistent logging with caller information:

```python
# Good: Centralized context logging
from logerr.utils import log

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
from logerr.utils import resolve

def retry_operation(max_attempts: int | None = None) -> None:
    actual_attempts = resolve(
        max_attempts, 
        default=3,
        validator=lambda x: x > 0
    )
```

### **Available Utility Functions**

| Function | Purpose | Common Use Cases |
|----------|---------|------------------|
| `execute()` | Execute callables with automatic Result/Option wrapping | Factory functions, risky operations |
| `nullable()` | Convert None values to appropriate types | Configuration loading, optional parameters |
| `validate()` | Predicate-based validation with consistent error handling | Input validation, constraint checking |
| `log()` | Context-aware logging with caller information | Error logging, debugging |
| `resolve()` | Parameter resolution with validation | Function parameters, configuration merging |
| `chain()` | Exception-safe method chaining | Monadic operations (map, and_then) |
| `attribute()` | Safe attribute access | Getting function names, object properties |
| `error()` | Standardized validation error messages | Consistent error formatting |

## API Structure

The library provides a clean, namespaced API:

### Direct Type Imports
```python
from logerr import Ok, Err, Some, Nothing, Result, Option
```

### Configuration Functions
```python
from logerr import configure, configure_from_confection, get_config, reset_config
```

### Factory Functions (Class Methods)
```python
from logerr import Result, Option

# Result factories
result = Result.from_callable(lambda: some_function())
result = Result.from_optional(maybe_value, "was None")

# Option factories  
option = Option.from_nullable(dict.get("key"))
option = Option.from_callable(lambda: expensive_computation())
option = Option.from_predicate(value, lambda x: x > 0)
```

### Configuration Examples
```python
# Basic configuration
logerr.configure({"level": "WARNING", "libraries": {"mylib": {"level": "DEBUG"}}})

# From configuration file
logerr.configure_from_confection("config.cfg")

# Get current configuration
config = logerr.get_config()

# Reset to defaults
logerr.reset_config()
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
   - `pixi run -e dev test` - Run test suite
   - `pixi run -e dev typecheck` - Run mypy type checking
   - `pixi run -e dev quality` - Run ruff lint + format checks

## Configuration

- **Platform**: macOS ARM64 (osx-arm64)
- **Package channels**: conda-forge
- **Environment**: Uses pixi for dependency management and virtual environments