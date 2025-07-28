# logerr

**Rust-like Option and Result types for Python with automatic logging**

[![Tests](https://img.shields.io/badge/tests-79%20passed-green)](https://github.com/jess-robertson/logerr)
[![Type Checked](https://img.shields.io/badge/mypy-passing-blue)](https://github.com/jess-robertson/logerr)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue)](https://github.com/jess-robertson/logerr)

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
import logerr
from logerr import Ok, Err, Some, Nothing

# Handle operations that might fail
result = logerr.result.from_callable(lambda: risky_database_call())
if result.is_ok():
    data = result.unwrap()
    print(f"Got data: {data}")
else:
    print("Operation failed - error details logged automatically!")

# Work with nullable values
config_value = logerr.option.from_nullable(os.environ.get("DATABASE_URL"))
db_url = config_value.unwrap_or("sqlite:///default.db")

# Chain operations elegantly
processed = (Ok("hello world")
    .map(str.upper)           # Ok("HELLO WORLD")  
    .map(lambda s: s.split()) # Ok(["HELLO", "WORLD"])
    .map(len)                 # Ok(2)
    .unwrap_or(0))            # 2
```

## 📦 Installation

Currently available from source:

```bash
git clone https://github.com/jess-robertson/logerr
cd logerr
pip install -e .
```

## 🔍 Why logerr?

Traditional Python error handling often forces difficult tradeoffs:

| Approach | Pros | Cons |
|----------|------|------|
| **Exceptions** | Clear error info | Can be hard to follow, requires try/catch |
| **None returns** | Simple | Loses error context, silent failures |
| **Tuple returns** | Explicit | Verbose, easy to misuse |

**logerr gives you the best of all worlds:**

✅ **Explicit error handling** like Go or Rust  
✅ **Composable operations** through method chaining  
✅ **Automatic observability** without manual logging  
✅ **Type safety** that catches errors at development time  

## 📖 Documentation

- **[Getting Started](https://jess-robertson.github.io/logerr/guide/getting-started/)** - Learn the basics
- **[Result Types](https://jess-robertson.github.io/logerr/guide/result-types/)** - Handle operations that might fail
- **[Option Types](https://jess-robertson.github.io/logerr/guide/option-types/)** - Work with nullable values  
- **[Configuration](https://jess-robertson.github.io/logerr/guide/configuration/)** - Customize logging behavior
- **[API Reference](https://jess-robertson.github.io/logerr/api/result/)** - Complete API documentation

## 💡 Examples

### Database Connection with Retry Logic

```python
import logerr
from typing import Any

def connect_to_database(url: str) -> logerr.Result[Any, str]:
    return logerr.result.from_callable(lambda: database.connect(url))

def with_retry(error: str) -> logerr.Result[Any, str]:
    if "timeout" in error.lower():
        return connect_to_database("backup-server.db")
    return logerr.Err(f"Connection failed: {error}")

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
import logerr
import json
from pathlib import Path

def load_config(path: str) -> logerr.Result[dict, str]:
    """Load and validate configuration file."""
    return (logerr.result.from_callable(lambda: Path(path).read_text())
        .and_then(lambda text: logerr.result.from_callable(lambda: json.loads(text)))
        .and_then(validate_config)
        .map_err(lambda e: f"Config error in {path}: {e}"))

def validate_config(config: dict) -> logerr.Result[dict, str]:
    required_keys = ["database_url", "api_key"]
    missing = [key for key in required_keys if key not in config]
    if missing:
        return logerr.Err(f"Missing required keys: {missing}")
    return logerr.Ok(config)

# Load with automatic error logging
config = load_config("app.json").unwrap_or({
    "database_url": "sqlite:///default.db",
    "api_key": "demo-key"
})
```

### Safe Data Processing

```python
import logerr

def process_user_data(data: dict) -> logerr.Option[str]:
    """Extract and format user display name."""
    return (logerr.option.from_nullable(data.get("user"))
        .and_then(lambda user: logerr.option.from_nullable(user.get("profile")))
        .and_then(lambda profile: logerr.option.from_nullable(profile.get("name")))
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

- Inspired by Rust's `Option` and `Result` types
- Built on the excellent [loguru](https://github.com/Delgan/loguru) logging library
- Configuration powered by [confection](https://github.com/explosion/confection)
- Similar to [option](https://github.com/MaT1g3R/option) but with automatic logging