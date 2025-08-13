# logerr

**Rust-like Option and Result types for Python with automatic logging**

`logerr` brings the power of Rust's `Option<T>` and `Result<T, E>` types to Python, with a unique twist: automatic logging of error cases using [loguru](https://github.com/Delgan/loguru). This allows you to write clean, functional error-handling code while maintaining excellent observability.

## Key Features

✨ **Rust-like Types**: Familiar `Option<T>` and `Result<T, E>` with full method chaining  
🪵 **Automatic Logging**: Error cases are logged automatically with configurable levels  
⚙️ **Highly Configurable**: Per-library configuration via [confection](https://github.com/explosion/confection)  
🔒 **Type Safe**: Full mypy support with proper generic types  
🧪 **Well Tested**: Comprehensive test suite with 79 tests including doctests  
🚀 **Easy to Use**: Clean, discoverable API with excellent IDE support  

## Quick Start

```python
import logerr
from logerr import Ok, Err, Some, Nothing

# Result types for operations that might fail
def risky_operation():
    raise ConnectionError("Database connection failed")

result = logerr.result.of(risky_operation)
if result.is_ok():
    print(f"Success: {result.unwrap()}")
else:
    print("Operation failed - check logs for details")
    # 🪵 Automatic logging output:
    # 2024-01-15 14:23:12.345 | ERROR | logerr.result:425 - Result error in risky_operation:2 - Database connection failed
```

**✨ The key difference:** Errors are **automatically logged** with full context!

```python
# Option types for nullable values  
config = {"name": "MyApp"}
db_url = logerr.option.from_nullable(config.get("database_url"))
connection_string = db_url.unwrap_or("sqlite:///default.db")
# 🪵 Automatic logging output:
# 2024-01-15 14:23:12.456 | WARNING | logerr.option:421 - Option Nothing in from_nullable:1 - Value was None

# Method chaining with automatic error handling
processed = (Ok("hello world")
    .map(str.upper)
    .map(lambda s: s.split())
    .map(len)
    .unwrap_or(0))
```

## Why logerr?

Traditional Python error handling often forces you to choose between:

- **Exceptions**: Great for errors, but can make control flow hard to follow
- **None returns**: Simple but lose error information and context
- **Tuple returns**: Verbose and easy to misuse

`logerr` gives you the best of all worlds:

- **Explicit error handling** like Go or Rust
- **Composable operations** through method chaining  
- **Automatic observability** without manual logging calls
- **Type safety** that catches errors at development time

## Installation

```bash
pip install logerr  # (when published)
```

For now, install from source:

```bash
git clone https://github.com/jesserobertson/logerr
cd logerr
pip install -e .
```

## Learn More

- [Getting Started Guide](guide/getting-started.md) - Learn the basics
- [Result Types](guide/result-types.md) - Handle operations that might fail  
- [Option Types](guide/option-types.md) - Work with nullable values
- [Configuration](guide/configuration.md) - Customize logging behavior
- [API Reference](api/result.md) - Complete API documentation

## Example: Real-World Usage

```python
import logerr
from pathlib import Path

def load_user_config(path: str) -> logerr.Result[dict, str]:
    """Load and parse user configuration file."""
    return (logerr.result.of(lambda: Path(path).read_text())
        .then(lambda text: logerr.result.of(lambda: json.loads(text)))
        .map_err(lambda e: f"Failed to load config from {path}: {e}"))

def get_database_url(config: dict) -> logerr.Option[str]:
    """Extract database URL from config."""
    return (logerr.option.from_nullable(config.get("database"))
        .then(lambda db: logerr.option.from_nullable(db.get("url"))))

# Usage
config_result = load_user_config("app.json")
if config_result.is_ok():
    config = config_result.unwrap()
    db_url = get_database_url(config).unwrap_or("sqlite:///default.db")
    print(f"Using database: {db_url}")
else:
    print("Using default configuration")
    # Error details are automatically logged!
```

This code is clean, composable, and provides excellent error visibility through automatic logging.

## Acknowledgments

This project builds upon excellent prior work:

- **[MaT1g3R/option](https://github.com/MaT1g3R/option)** - The original Python implementation of Rust-like Option and Result types that inspired this project. `logerr` extends their elegant API design with automatic logging capabilities.
- **[Rust's std::option and std::result](https://doc.rust-lang.org/)** - The foundational design patterns and method names
- **[loguru](https://github.com/Delgan/loguru)** - The excellent logging library that powers our automatic error logging