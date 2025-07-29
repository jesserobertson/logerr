# logerr

**Rust-like Option and Result types for Python with automatic logging**

[![Tests](https://img.shields.io/badge/tests-162%20passed-green)](https://github.com/jesserobertson/logerr)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)](https://github.com/jesserobertson/logerr)
[![Type Checked](https://img.shields.io/badge/mypy-passing-blue)](https://github.com/jesserobertson/logerr)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue)](https://github.com/jesserobertson/logerr)

`logerr` brings the power of Rust's `Option<T>` and `Result<T, E>` types to Python, with automatic logging of error cases using [loguru](https://github.com/Delgan/loguru). Write clean, functional error-handling code while maintaining excellent observability.

## 🌟 Features

- **🦀 Rust-like Types**: Familiar `Option<T>` and `Result<T, E>` with method chaining
- **🪵 Automatic Logging**: Error cases logged automatically with configurable levels  
- **⚙️ Highly Configurable**: Per-library settings via [confection](https://github.com/explosion/confection)
- **🔒 Type Safe**: Full mypy support with proper generic types
- **🧪 Well Tested**: 79 tests including comprehensive doctests
- **🚀 Clean API**: Discoverable, IDE-friendly interface

## 🚀 Quick Start

```python
from logerr import Result, Ok, Err, Some, Nothing

# Handle operations that might fail
def risky_operation():
    raise ConnectionError("Database connection failed")

result_value = Result.from_callable(risky_operation)
if result_value.is_ok():
    print(f"Success: {result_value.unwrap()}")
else:
    print(f"Failed: {result_value.unwrap_or('unknown error')}")
    # 🪵 Automatic logging output:
    # 2024-01-15 14:23:12.345 | ERROR | logerr.result:425 - Result error in risky_operation:2 - Database connection failed
```

**✨ The key difference:** Errors are **automatically logged** with full context - no manual logging required!

```python
from logerr import Option

# Work with optional values
user_data = {"name": "Alice"}
email = Option.from_nullable(user_data.get("email"))
contact = email.unwrap_or("no-email@example.com")
# 🪵 Automatic logging output:
# 2024-01-15 14:23:12.456 | WARNING | logerr.option:421 - Option Nothing in from_nullable:1 - Value was None

# Chain operations elegantly with automatic error handling
processed = (Ok("hello world")
    .map(str.upper)           # Ok("HELLO WORLD")  
    .map(lambda s: s.split()) # Ok(["HELLO", "WORLD"])
    .map(len)                 # Ok(2)
    .unwrap_or(0))            # 2
```

## 📦 Installation

Currently available from source:

```bash
git clone https://github.com/jesserobertson/logerr
cd logerr
pip install -e .
```

## 🔍 Why logerr?

### See the Difference

**Traditional approach** (manual logging required):
```python
def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")  # Manual logging
        return None

config = load_config()
if config is None:
    print("Using defaults")
```

**With logerr** (automatic logging):
```python
from logerr import Result

def load_config():
    return Result.from_callable(lambda: json.load(open("config.json")))

config = load_config().unwrap_or({})
# 🪵 Automatically logs:
# 2024-01-15 14:23:12.789 | ERROR | logerr.result:425 - Result error in <lambda>:1 - [Errno 2] No such file or directory: 'config.json'
```

### Traditional Tradeoffs vs logerr

| Approach | Pros | Cons |
|----------|------|------|
| **Exceptions** | Clear error info | Hard to follow, requires try/catch |
| **None returns** | Simple | Loses error context, silent failures |
| **Tuple returns** | Explicit | Verbose, easy to misuse |
| **🦀 logerr** | **Explicit + Automatic logging + Composable + Type safe** | **Learning curve** |

**logerr gives you the best of all worlds:**

✅ **Explicit error handling** like Go or Rust  
✅ **Composable operations** through method chaining  
✅ **Automatic observability** without manual logging  
✅ **Type safety** that catches errors at development time  

## 📖 Documentation

- **[Getting Started](https://jesserobertson.github.io/logerr/guide/getting-started/)** - Learn the basics
- **[Result Types](https://jesserobertson.github.io/logerr/guide/result-types/)** - Handle operations that might fail
- **[Option Types](https://jesserobertson.github.io/logerr/guide/option-types/)** - Work with nullable values  
- **[Configuration](https://jesserobertson.github.io/logerr/guide/configuration/)** - Customize logging behavior
- **[API Reference](https://jesserobertson.github.io/logerr/api/result/)** - Complete API documentation

## 💡 Examples

### Database Connection with Retry Logic

```python
from logerr import Result, Err
from typing import Any

def connect_to_database(url: str) -> Result[Any, str]:
    return Result.from_callable(lambda: database.connect(url))

def with_retry(error: str) -> Result[Any, str]:
    if "timeout" in error.lower():
        return connect_to_database("backup-server.db")
    return Err(f"Connection failed: {error}")

# Automatic retry with logging
connection = (connect_to_database("primary-server.db")
    .or_else(with_retry)
    .unwrap_or(None))

if connection:
    print("Connected successfully!")
else:
    print("All connection attempts failed - check logs")
```

### Configuration Loading Pipeline

```python
from logerr import Result, Ok, Err
import json
from pathlib import Path

def load_config(path: str) -> Result[dict, str]:
    """Load and validate configuration file."""
    return (Result.from_callable(lambda: Path(path).read_text())
        .and_then(lambda text: Result.from_callable(lambda: json.loads(text)))
        .and_then(validate_config)
        .map_err(lambda e: f"Config error in {path}: {e}"))

def validate_config(config: dict) -> Result[dict, str]:
    required_keys = ["database_url", "api_key"]
    missing = [key for key in required_keys if key not in config]
    if missing:
        return Err(f"Missing required keys: {missing}")
    return Ok(config)

# Load with automatic error logging
config = load_config("app.json").unwrap_or({
    "database_url": "sqlite:///default.db",
    "api_key": "demo-key"
})
```

### Safe Data Processing

```python
from logerr import Option

def process_user_data(data: dict) -> Option[str]:
    """Extract and format user display name."""
    return (Option.from_nullable(data.get("user"))
        .and_then(lambda user: Option.from_nullable(user.get("profile")))
        .and_then(lambda profile: Option.from_nullable(profile.get("name")))
        .filter(lambda name: len(name.strip()) > 0)
        .map(str.title))

# Usage
user_data = {"user": {"profile": {"name": "alice smith"}}}
display_name = process_user_data(user_data).unwrap_or("Anonymous User")
print(f"Hello, {display_name}!")  # Hello, Alice Smith!
```

## ⚙️ Configuration

Customize logging behavior per library:

```python
import logerr

# Global configuration
logerr.configure({
    "enabled": True,
    "level": "WARNING",
    "format": "Error in {function}: {error}",
    "capture_locals": False
})

# Per-library configuration  
logerr.configure({
    "libraries": {
        "myapp.database": {"level": "ERROR"},
        "myapp.api": {"level": "DEBUG"},
        "third_party_lib": {"enabled": False}
    }
})
```

## 🧪 Development

This project uses [pixi](https://pixi.sh) for development:

```bash
# Install dependencies
pixi install

# Run tests
pixi run -e dev test

# Run tests with doctests
pixi run -e dev test-all

# Type checking
pixi run -e dev typecheck

# Build documentation
pixi run -e docs docs-build

# Serve documentation locally
pixi run -e docs docs-serve
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

This project builds upon excellent prior work:

- **[MaT1g3R/option](https://github.com/MaT1g3R/option)** - The original Python implementation of Rust-like Option and Result types that inspired this project. `logerr` extends their elegant API design with automatic logging capabilities.
- **[Rust's std::option and std::result](https://doc.rust-lang.org/)** - The foundational design patterns and method names
- **[loguru](https://github.com/Delgan/loguru)** - The excellent logging library that powers our automatic error logging
- **[confection](https://github.com/explosion/confection)** - Flexible configuration management system