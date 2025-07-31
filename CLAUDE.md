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

### Testing and Quality
- `pixi run -e dev test` - Run test suite
- `pixi run -e dev test-all` - Run tests including doctests
- `pixi run -e dev typecheck` - Run type checking with mypy
- `pixi run -e dev quality` - Run code quality checks (ruff lint + format check)
- `pixi run -e dev check-all` - Run all checks (test, typecheck, quality) - **REQUIRED BEFORE COMMITS**

### Documentation
- `pixi run -e docs docs-serve` - Serve documentation locally
- `pixi run -e docs docs-build` - Build documentation

### Package Management
- Add dependencies: `pixi add <package-name>`
- Add development dependencies: `pixi add --feature dev <package-name>`
- Add documentation dependencies: `pixi add --feature docs <package-name>`
- Remove dependencies: `pixi remove <package-name>`

## Project Structure

```
logerr/
├── logerr/           # Main library package
│   ├── __init__.py   # Main exports (Option, Some, Nothing, Result, Ok, Err)
│   ├── option.py     # Option<T>, Some<T>, Nothing implementation
│   ├── result.py     # Result<T, E>, Ok<T>, Err<E> implementation
│   ├── config.py     # Configuration management via confection
│   └── protocols.py  # Type protocols for comparison support
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
│   └── test_result.py
├── mkdocs.yml        # Documentation configuration
├── pixi.toml         # Project configuration and dependencies
├── README.md         # Project README
└── CLAUDE.md         # This file
```

## Dependencies

### Runtime Dependencies
- **loguru**: Automatic logging of Result/Err cases
- **confection**: Configuration management

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