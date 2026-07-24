# logerr

**Rust-like Option and Result types for Python with automatic logging**

[![Tests](https://img.shields.io/badge/tests-566%20passed-green)](https://github.com/jesserobertson/logerr)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](https://github.com/jesserobertson/logerr)
[![Type Checked](https://img.shields.io/badge/mypy-passing-blue)](https://github.com/jesserobertson/logerr)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)](https://github.com/jesserobertson/logerr)

`logerr` brings the power of Rust's `Option<T>` and `Result<T, E>` types to Python, with automatic logging of error cases using [loguru](https://github.com/Delgan/loguru). Write clean, functional error-handling code while maintaining excellent observability.

## 🌟 Features

- **🦀 Rust-like Types**: Familiar `Option<T>` and `Result<T, E>` with method chaining
- **🔗 Full Combinator Set**: `zip()`, `flatten()`, `and_()`, `or_()`, `ok()`, `err()` alongside the core `map`/`then`/`filter`
- **🪵 Automatic Logging**: Error cases logged automatically with configurable levels  
- **⚙️ Highly Configurable**: Per-library settings via [confection](https://github.com/explosion/confection)
- **🔒 Type Safe**: Full mypy support with proper generic types
- **🧪 Well Tested**: 500+ tests including property-based tests and comprehensive doctests
- **🚀 Clean API**: Discoverable, IDE-friendly interface

## 🚀 Quick Start

```python
>>> from logerr import Result, Ok, Err, Some, Nothing

>>> # Simple successful case
>>> success = Ok(42)
>>> success.map(lambda x: x * 2).unwrap()
84

>>> # Error case with fallback
>>> error = Err("something failed")
>>> error.unwrap_or("default value")
'default value'

>>> # Chain operations elegantly
>>> Ok("hello").map(str.upper).map(len).unwrap()
5

```

**✨ The key difference:** Errors are **automatically logged** with full context - no manual logging required!

```python
>>> from logerr import Option

>>> # Work with optional values using functional pipeline
>>> user_data = {"name": "Alice"}

>>> # Functional pipeline for nullable values
>>> contact = (
...     Option.from_nullable(user_data.get("email"))
...     .filter(lambda email: "@" in email)  # Validate email format
...     .unwrap_or("no-email@example.com")
... )
>>> print(contact)
no-email@example.com

>>> # Chain operations elegantly with automatic error handling
>>> processed = (
...     Ok("hello world")
...     .map(str.upper)           # Ok("HELLO WORLD")  
...     .map(lambda s: s.split()) # Ok(["HELLO", "WORLD"])
...     .map(len)                 # Ok(2)
...     .unwrap_or(0)            # 2
... )
>>> print(processed)
2

```

## 📦 Installation

Currently available from source:

```bash
git clone https://github.com/jesserobertson/logerr
cd logerr
pip install -e .
```

### Optional Features

**Recipes Module**: Advanced patterns and utilities for specialized use cases:

```bash
# Install retry patterns (tenacity)
pixi run -e retry  # or: pip install "logerr[retry]"

# Install dataframe/table conversion utilities (pymongo, pandas)
pixi run -e tables  # or: pip install "logerr[tables]"

# Use in your code
from logerr.recipes import retry, config

@retry.on_err()  # retries on Err, default: 3 attempts with exponential backoff
def flaky_operation() -> Result[int, str]:
    return Ok(42)

# Functional utilities (no extra install needed - these are core)
from logerr.utilities import validate, pipe, try_chain

config.configure_advanced({"libraries": {"my_module": {"level": "DEBUG"}}})

# NoSQL to DataFrame conversion with data quality logging
from logerr.recipes.dataframes import Required, from_mongo

schema = {"user_id": Required[str], "email": Required[str], "name": str}
df = from_mongo(db.users, {"status": "active"}, schema=schema).unwrap_or(pd.DataFrame())
```

## 🔍 Why logerr?

### See the Difference

**Traditional approach** (manual logging required):
```python
>>> import json
>>> def load_config():
...     try:
...         with open("config.json") as f:
...             return json.load(f)
...     except Exception as e:
...         print(f"Failed to load config: {e}")  # Manual logging
...         return None

>>> config = load_config()  # doctest: +SKIP
>>> if config is None:  # doctest: +SKIP
...     print("Using defaults")  # doctest: +SKIP
```

**With logerr** (automatic logging + functional style):
```python
>>> from logerr import Result
>>> from logerr.utilities import execute
>>> import json

>>> def load_config():
...     return execute(lambda: json.load(open("config.json")))

>>> # Functional pipeline with error recovery
>>> config = (
...     load_config()
...     .unwrap_or({})  # Fallback to empty config
... )
>>> print(type(config))
<class 'dict'>

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
from logerr import Result, Ok, Err
from logerr.recipes import retry  # pixi install -e retry (or pip install "logerr[retry]")
from typing import Any

@retry.on_err()  # retries on Err, default: 3 attempts with exponential backoff
def connect_to_database(url: str) -> Result[Any, Exception]:
    try:
        return Ok(database.connect(url))
    except ConnectionError as e:
        return Err.from_exception(e)

# Alternative: functional retry utility instead of the decorator
def connect_with_fallback() -> Result[Any, Exception]:
    return retry.with_retry(lambda: database.connect("primary-server.db")).or_else(
        lambda _: retry.with_retry(lambda: database.connect("backup-server.db"))
    )

result = (
    connect_to_database("primary-server.db")
    .map(lambda conn: "Connected successfully!")
    .unwrap_or("All connection attempts failed - check logs")
)
```

### Configuration Loading Pipeline

```python
from logerr import Result, Ok
from logerr.utilities import execute, validate, resolve

def load_config(path: str) -> Result[dict, str]:
    return (
        execute(lambda: open(path).read())
        .then(lambda text: execute(lambda: json.loads(text)))
        .then(validate_config)
        .map_err(lambda e: f"Config error in {path}: {e}")
    )

def validate_config(config: dict) -> Result[dict, str]:
    required = ["database_url", "api_key"]
    return (
        validate(config, lambda cfg: all(k in cfg for k in required), error_factory=None)
        .map_err(lambda _: f"Missing keys: {[k for k in required if k not in config]}")
        .map(lambda _: config)
    )

# Functional pipeline with fallback configuration
default_config = {"database_url": "sqlite:///default.db", "api_key": "demo-key"}

config = (
    load_config("app.json")
    .or_else(lambda _: Ok(default_config))
    .map(lambda cfg: resolve(cfg.get("database_url"), default=default_config["database_url"]))
    .unwrap()
)
```

### Safe Data Processing

```python
from logerr import Option
from logerr.utilities import nullable, validate, attribute

def process_user_data(data: dict) -> Option[str]:
    return (
        nullable(data.get("user"))
        .then(lambda user: nullable(user.get("profile")))
        .then(lambda profile: nullable(profile.get("name")))
        .then(lambda name: validate(name, lambda n: len(n.strip()) > 0, error_factory=None, return_type="option"))
        .map(str.title)
        .map(lambda name: f"👋 {name}")
    )

def get_user_role(data: dict) -> Option[str]:
    return (
        nullable(data.get("user"))
        .map(lambda user: attribute(user, "role", "member"))  # default to "member"
        .filter(lambda role: role in ["admin", "member", "guest"])
    )

user_data = {"user": {"profile": {"name": "alice smith"}, "role": "admin"}}

greeting = (
    process_user_data(user_data)
    .then(lambda name: get_user_role(user_data).map(lambda role: f"{name} (Role: {role})"))
    .unwrap_or("👋 Anonymous User")
)
# greeting == "👋 Alice Smith (Role: admin)"
```

### NoSQL to DataFrame with Data Quality Logging

```python
from logerr.recipes.dataframes import Required, from_mongo
from logerr import configure

configure(level="INFO")  # data quality reports log at INFO

# Required fields error if missing; other fields are optional by default
schema = {
    "user_id": Required[str],
    "email": Required[str],
    "name": str,
    "age": int,
}

result = from_mongo(
    collection=db.users,
    query={"status": "active", "last_login": {"$gte": last_month}},
    schema=schema,
    report_name="active_users",
)

df = (
    result
    .map(lambda df: df[df["age"].notna()])  # drop rows missing age
    .unwrap_or_else(lambda error: handle_data_error(error))
)

# Automatic logging output:
# INFO    | Data Quality Summary for 'active_users': 1847/2000 records processed successfully (92.4%)
# ERROR   | Missing required field 'email' in 153/2000 records - excluding from DataFrame
```

## ⚙️ Configuration

**Core Configuration** (simple and lightweight):

```python
>>> import logerr

>>> # Basic configuration - just the essentials
>>> result = logerr.configure(enabled=True, level="WARNING")
>>> result.is_ok()
True

>>> # Just change log level
>>> result = logerr.configure(level="INFO")
>>> result.is_ok()
True

```

**Advanced Configuration** (per-library settings, custom formats, file-based
config — no extra install needed, `confection` is already a core dependency;
this just lives under `logerr.recipes.config` to keep the top-level API
small):

```python
from logerr.recipes.config import configure_advanced, configure_from_confection

configure_advanced({
    "level": "WARNING",
    "libraries": {
        "myapp.database": {"level": "ERROR"},
        "myapp.api": {"level": "DEBUG"},
        "third_party_lib": {"enabled": False},
    },
    "capture_locals": True,
})

# Or load the same settings from a confection config file (see the
# Configuration guide for the expected [logerr] file format)
configure_from_confection("config.cfg")
```

## 🧪 Development

This project uses [pixi](https://pixi.sh) for development:

```bash
# Install dependencies
pixi install

# Install with retry/tables extras for advanced patterns and utilities
pixi install -e retry
pixi install -e tables

# Run fast tests
pixi run -e dev test fast

# Run all tests, including doctests
pixi run -e dev test all

# Type checking
pixi run -e dev quality typecheck

# Build documentation (default environment - combines dev + docs features)
pixi run docs build

# Serve documentation locally
pixi run docs serve
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
- **[tenacity](https://github.com/jd/tenacity)** - Robust retry library that powers our retry decorators and resilient operations